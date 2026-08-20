import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

/** A regular event row, and the sub-event rows of an expanded swap. */
export const EVENT_ROW = '[data-testid=history-event-row]';

/** A swap group, collapsed or expanded — the id is on the collapse header too. */
export const SWAP_ROW = '[data-testid=history-event-swap]';

/** A movement that paired with another one and renders as a single matched row. */
export const MOVEMENT_ROW = '[data-testid=history-event-movement]';

/**
 * Addressing, reading and acting on the rows of the history events table.
 *
 * Split out of `HistoryEventsPage` because it is one concern with one rule behind it: **a row is
 * named by the event it stands for, never by its position**. The table sorts timestamp DESC and
 * re-renders on every write, so an index resolved before a mutation names a different event after
 * it. That is not a stylistic preference — it is how the edit action ends up clicking the wrong
 * row, and how an assertion ends up reading one.
 *
 * The rule has a second half, which `waitForNewRow` exists to enforce: **an id resolved too early
 * names the wrong event, and pinning it does not save you.** A save is followed by a refetch, and
 * for as long as that is in flight the table still holds the previous rows. Waiting for a row
 * *count* does not close that window — the specs run serial against a shared page, so any
 * `>= n` guard is already satisfied by the rows earlier tests left behind and passes on the first
 * tick. Wait for the event itself.
 */
export class HistoryEventRows {
  constructor(private readonly page: Page) {}

  async countEvents(): Promise<number> {
    return this.page.locator(EVENT_ROW).count();
  }

  async countSwaps(): Promise<number> {
    return this.page.locator(SWAP_ROW).count();
  }

  async countMovements(): Promise<number> {
    return this.page.locator(MOVEMENT_ROW).count();
  }

  /** The event ids currently rendered for `rowSelector`, in DOM order. */
  async idsOf(rowSelector: string): Promise<string[]> {
    const ids = await this.page.locator(rowSelector).evaluateAll(rows =>
      rows.map(row => row.getAttribute('data-event-id')));
    return ids.filter((id): id is string => !!id);
  }

  /**
   * Waits for a row that is not one of `idsBefore` and pins it by its id.
   *
   * This is the gate to use after saving a new event: it is false until that event renders, which
   * is what a count guard is not. Capture `idsBefore` with `idsOf` before opening the dialog, so
   * the comparison spans the whole save.
   */
  async waitForNewRow(idsBefore: string[], rowSelector: string): Promise<Locator> {
    const seen = new Set(idsBefore);
    let added: string | undefined;

    await expect(async () => {
      added = (await this.idsOf(rowSelector)).find(id => !seen.has(id));
      expect(added, `no new ${rowSelector} appeared`).toBeTruthy();
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    return this.byId(added ?? '');
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
   * result from then on. ⚠️ Only valid where the top row is already the one you mean: after a save
   * the refetch may still be in flight, and this then pins the *previous* top row. Use
   * `waitForNewRow` there.
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

  /** Expands an already-resolved swap row, so which group opens does not depend on its position. */
  async expand(row: Locator): Promise<void> {
    await row.hover();
    await row.locator('[data-testid=swap-expand]').click();
  }

  async delete(row: Locator): Promise<void> {
    await row.hover();
    await row.locator('[data-testid=row-delete]').click();
    const dialog = this.page.locator('[data-testid=confirm-dialog]');
    await dialog.locator('[data-testid=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }
}
