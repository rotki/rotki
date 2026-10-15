import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

type RowStatus = 'cancelled' | 'complete' | 'failed' | 'pending' | 'running' | 'skipped';

/** The corner task dock: its pill, its panel, and the stop confirmations it asks in place. */
export class TaskDockPage {
  private readonly pill: Locator;
  private readonly panel: Locator;

  constructor(private readonly page: Page) {
    this.pill = page.getByTestId('task-dock-pill');
    this.panel = page.getByTestId('task-dock-panel');
  }

  /**
   * Opens the panel, whether or not the dock already opened it for a job the user started.
   *
   * @remarks
   * Retried as a whole: the dock may open itself between the visibility check and the click, and
   * the click then folds it again.
   */
  async openPanel(): Promise<void> {
    await expect(async () => {
      if (!(await this.panel.isVisible()))
        await this.pill.click();
      await expect(this.panel).toBeVisible({ timeout: 1000 });
    }).toPass({ timeout: TIMEOUT_MEDIUM });
  }

  /**
   * A job's row, found by its title whether the row shows it as the label or the line under it.
   *
   * @remarks
   * Matched on the `title` attribute the label and that line carry, not on the row's text: a graph
   * row lists its lanes by name in its breakdown, so the login's "Blockchain balances" row also
   * contains the text "All balances".
   */
  private row(title: string): Locator {
    return this.panel.getByTestId('dock-activity-row').filter({ has: this.page.getByTitle(title, { exact: true }) });
  }

  async expectRow(label: string, status: RowStatus): Promise<void> {
    await expect(this.row(label)).toHaveAttribute('data-status', status, { timeout: TIMEOUT_MEDIUM });
  }

  async expectRowMeter(label: string, text: string): Promise<void> {
    await expect(this.row(label).getByTestId('activity-meter')).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  async expectStopAllOffered(offered: boolean): Promise<void> {
    const button = this.panel.getByTestId('dock-stop-all');
    if (offered)
      await expect(button).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    else
      await expect(button).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  /** Asks to stop all, leaving the footer's question open. */
  async stopAll(): Promise<void> {
    await this.panel.getByTestId('dock-stop-all').click();
    await expect(this.panel.getByTestId('dock-stop-all-confirm')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectStopAllPrompt(message: string | RegExp): Promise<void> {
    await expect(this.panel.getByTestId('dock-stop-all-confirm')).toContainText(message);
  }

  async keepAllRunning(): Promise<void> {
    await this.panel.getByTestId('dock-keep-running').click();
    await expect(this.panel.getByTestId('dock-stop-all-confirm')).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  async confirmStopAll(): Promise<void> {
    await this.panel.getByTestId('dock-stop-all-confirmed').click();
    await expect(this.panel.getByTestId('dock-stop-all-confirm')).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  /** Asks to stop one row, leaving the row's question open. */
  async cancelRow(label: string): Promise<void> {
    await this.row(label).getByTestId('cancel-activity').click();
    await expect(this.row(label).getByTestId('activity-stop-confirm')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectRowStopPrompt(label: string, message: string | RegExp): Promise<void> {
    await expect(this.row(label).getByTestId('activity-stop-confirm')).toContainText(message);
  }

  async confirmRowStop(label: string): Promise<void> {
    await this.row(label).getByTestId('activity-stop').click();
  }
}
