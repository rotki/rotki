import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

async function confirmDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-cy=bottom-dialog]');
  await dialog.locator('[data-cy=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-cy=confirm-dialog]');
  await confirmDialogEl.locator('[data-cy=button-confirm]').click();
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
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async cancelDialog(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.locator('[data-cy=cancel]').click();
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

  async createEvent(opts: { name: string; description?: string }): Promise<void> {
    await this.openAddDialog();
    await this.page.getByTestId('calendar-form-name').locator('input').fill(opts.name);
    if (opts.description !== undefined) {
      await this.page.getByTestId('calendar-form-description').locator('textarea').first().fill(opts.description);
    }
    await confirmDialog(this.page);
  }

  async openEventByName(name: string): Promise<void> {
    // Click "View details" on the matching event in the selected-events panel.
    const event = this.eventInPanel(this.selectedPanel(), name).first();
    await event.getByRole('button', { name: /view details/i }).click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
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
