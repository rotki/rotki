import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

async function confirmDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-testid=bottom-dialog]');
  await dialog.locator('[data-testid=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-testid=confirm-dialog]');
  await confirmDialogEl.locator('[data-testid=button-confirm]').click();
  await confirmDialogEl.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

export class CalendarPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'calendar');
  }

  selectedPanel() {
    return this.page.getByTestId('calendar-selected-list');
  }

  upcomingPanel() {
    return this.page.getByTestId('calendar-upcoming-list');
  }

  private eventInPanel(panel: ReturnType<CalendarPage['selectedPanel']>, name: string) {
    return panel.locator('[data-event-name]').filter({ hasText: name });
  }

  async openAddDialog(): Promise<void> {
    await this.page.getByTestId('calendar-add-event').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async cancelDialog(): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.locator('[data-testid=cancel]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async clickToday(): Promise<void> {
    await this.page.getByTestId('calendar-today').click();
    await this.page.waitForTimeout(150);
  }

  async expectTodayDisabled(): Promise<void> {
    await expect(this.page.getByTestId('calendar-today')).toBeDisabled();
  }

  async expectTodayEnabled(): Promise<void> {
    await expect(this.page.getByTestId('calendar-today')).toBeEnabled();
  }

  /** Fills the event fields of an already-open dialog, without submitting it. */
  async createEventFields(opts: { name: string; description?: string }): Promise<void> {
    await this.page.getByTestId('calendar-form-name').locator('input').fill(opts.name);
    if (opts.description !== undefined) {
      await this.page.getByTestId('calendar-form-description').locator('textarea').first().fill(opts.description);
    }
  }

  async createEvent(opts: { name: string; description?: string }): Promise<void> {
    await this.openAddDialog();
    await this.createEventFields(opts);
    await confirmDialog(this.page);
  }

  async openEventByName(name: string): Promise<void> {
    // Click "View details" on the matching event in the selected-events panel.
    const event = this.eventInPanel(this.selectedPanel(), name).first();
    await event.getByRole('button', { name: /view details/i }).click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async editEvent(name: string, opts: { newName?: string; newDescription?: string }): Promise<void> {
    await this.openEventByName(name);
    if (opts.newName !== undefined) {
      const input = this.page.getByTestId('calendar-form-name').locator('input');
      await input.fill(opts.newName);
    }
    if (opts.newDescription !== undefined) {
      const textarea = this.page.getByTestId('calendar-form-description').locator('textarea').first();
      await textarea.fill(opts.newDescription);
    }
    await confirmDialog(this.page);
  }

  async deleteEvent(name: string): Promise<void> {
    await this.openEventByName(name);
    await this.page.getByTestId('calendar-form-delete').click();
    await confirmDelete(this.page);
  }

  /** Scoped to the dialog: a page-wide match also picks up a closing dialog's rows. */
  private reminderRows() {
    return this.page.locator('[data-testid=bottom-dialog] [data-testid=reminder-amount]');
  }

  /** Adds a reminder to the dialog that is already open, and sets it to `amount` of `unit`. */
  async addReminder(amount: string, unit: string): Promise<void> {
    await this.page.getByTestId('reminder-add').click();
    const row = this.reminderRows().last();
    await row.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    const input = row.locator('input');
    await input.fill(amount);
    // A new row starts at the 15 minute default, and the amount field reformats as it is typed, so
    // the fill can be observed part-applied. Settling here reports it as what it is rather than as
    // a wrong value read back several steps later.
    await expect(input).toHaveValue(amount, { timeout: TIMEOUT_MEDIUM });

    // RuiMenuSelect opens a teleported menu rather than a native select.
    await this.page.getByTestId('reminder-unit').last().locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]');
    await menu.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    const option = menu.getByText(new RegExp(`^${unit}$`, 'i'));
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await option.click();
    await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_MEDIUM });
  }

  private reminderUnits() {
    return this.page.locator('[data-testid=bottom-dialog] [data-testid=reminder-unit]');
  }

  async expectReminder(amount: string, unit: string): Promise<void> {
    await expect(this.reminderRows().first().locator('input')).toHaveValue(amount, { timeout: TIMEOUT_MEDIUM });
    await expect(this.reminderUnits().first()).toContainText(unit);
  }

  async expectReminderCount(count: number): Promise<void> {
    await expect(this.reminderRows()).toHaveCount(count, { timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Opens the reminder list, which a reopened event starts with collapsed.
   *
   * The accordion is eager, so a collapsed list still has its rows in the DOM and Playwright reads
   * them as visible: the clipping is on an ancestor, not on the row. A click then lands on whatever
   * covers the collapsed strip, and retries until the test times out. Expanding first is what makes
   * the rows reachable, so every interaction with an existing row goes through here.
   */
  private async expandReminders(): Promise<void> {
    const toggle = this.page.locator('[data-testid=bottom-dialog] [data-testid=reminder-toggle]');
    if (await toggle.getAttribute('data-expanded') === 'true')
      return;

    await toggle.click();
    await expect(toggle).toHaveAttribute('data-expanded', 'true', { timeout: TIMEOUT_MEDIUM });
  }

  /** Retypes the amount of the row currently showing `amount`, and leaves the field. */
  async changeReminderAmount(from: string, to: string): Promise<void> {
    await this.expandReminders();
    const input = this.reminderRows().locator(`input[value="${from}"]`).first();
    await input.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await input.fill(to);
    await expect(input).toHaveValue(to, { timeout: TIMEOUT_MEDIUM });
    await input.blur();
  }

  async deleteReminder(amount: string): Promise<void> {
    await this.expandReminders();
    const row = this.reminderRows()
      .filter({ has: this.page.locator(`input[value="${amount}"]`) })
      .locator('xpath=..');
    await row.getByTestId('reminder-delete').click();
  }

  async expectReminderAmounts(amounts: string[]): Promise<void> {
    await expect(this.reminderRows()).toHaveCount(amounts.length, { timeout: TIMEOUT_MEDIUM });
    for (const [index, amount] of amounts.entries())
      await expect(this.reminderRows().nth(index).locator('input')).toHaveValue(amount, { timeout: TIMEOUT_MEDIUM });
  }

  /** Submits without waiting for the dialog to close, for the cases where it must not. */
  async submitDialog(): Promise<void> {
    await this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
  }

  async expectDialogOpen(): Promise<void> {
    await expect(this.page.locator('[data-testid=bottom-dialog]')).toBeVisible();
  }

  async expectReminderError(message: string): Promise<void> {
    await expect(this.page.locator('[data-testid=bottom-dialog]').getByText(message)).toBeVisible({
      timeout: TIMEOUT_MEDIUM,
    });
  }

  async confirmDialog(): Promise<void> {
    await confirmDialog(this.page);
  }

  async expectEventInSelected(name: string): Promise<void> {
    await expect(this.eventInPanel(this.selectedPanel(), name).first()).toBeVisible();
  }

  async expectNoEventInSelected(name: string): Promise<void> {
    await expect(this.eventInPanel(this.selectedPanel(), name)).toHaveCount(0);
  }

  async expectEventInUpcoming(name: string): Promise<void> {
    await expect(this.eventInPanel(this.upcomingPanel(), name).first()).toBeVisible();
  }

  async expectNoEventInUpcoming(name: string): Promise<void> {
    await expect(this.eventInPanel(this.upcomingPanel(), name)).toHaveCount(0);
  }

  async goToNextMonth(): Promise<void> {
    await this.page.getByTestId('calendar-next-month').click();
    await this.page.waitForTimeout(150);
  }

  async goToPrevMonth(): Promise<void> {
    await this.page.getByTestId('calendar-prev-month').click();
    await this.page.waitForTimeout(150);
  }

  async currentMonthLabel(): Promise<string> {
    const value = await this.page.getByTestId('calendar-month-label').locator('input').inputValue();
    return value;
  }

  async expectMonthLabel(label: string): Promise<void> {
    await expect(this.page.getByTestId('calendar-month-label').locator('input')).toHaveValue(label, { timeout: TIMEOUT_SHORT });
  }
}
