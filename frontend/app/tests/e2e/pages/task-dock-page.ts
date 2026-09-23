import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

type RowStatus = 'complete' | 'failed' | 'pending' | 'running' | 'skipped';

/** The corner task dock: its pill, its panel, and the Stop all confirmation it raises. */
export class TaskDockPage {
  private readonly pill: Locator;
  private readonly panel: Locator;
  private readonly dialog: Locator;

  constructor(private readonly page: Page) {
    this.pill = page.getByTestId('task-dock-pill');
    this.panel = page.getByTestId('task-dock-panel');
    this.dialog = page.getByTestId('confirm-dialog');
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

  /** A job's row, found by its title whether the row shows it as the label or the line under it. */
  private row(title: string): Locator {
    return this.panel.getByTestId('dock-activity-row').filter({ hasText: title });
  }

  async expectRow(label: string, status: RowStatus): Promise<void> {
    await expect(this.row(label)).toHaveAttribute('data-status', status, { timeout: TIMEOUT_MEDIUM });
  }

  /** A job the user stopped leaves the panel rather than staying as a settled row. */
  async expectNoRow(title: string): Promise<void> {
    await expect(this.row(title)).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
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

  async stopAll(): Promise<void> {
    await this.panel.getByTestId('dock-stop-all').click();
    await expect(this.dialog).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async cancelRow(label: string): Promise<void> {
    await this.row(label).getByTestId('cancel-activity').click();
    await expect(this.dialog).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectDialog(title: string, message: string): Promise<void> {
    await expect(this.dialog.getByTestId('dialog-title')).toHaveText(title);
    await expect(this.dialog).toContainText(message);
  }

  async expectDialogNotToMention(text: string): Promise<void> {
    await expect(this.dialog).toBeVisible();
    await expect(this.dialog).not.toContainText(text);
  }

  async dismissDialog(): Promise<void> {
    await this.dialog.getByTestId('button-cancel').click();
    await expect(this.dialog).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  async confirmDialog(): Promise<void> {
    await this.dialog.getByTestId('button-confirm').click();
    await expect(this.dialog).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }
}
