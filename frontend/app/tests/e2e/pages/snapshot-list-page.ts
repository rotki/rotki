import { expect, type Page } from '@playwright/test';
import { RotkiApp } from './rotki-app';
import { SnapshotEditorPage } from './snapshot-editor-page';

/**
 * The snapshot list page (`/statistics/snapshots`): the manager's index, sourced
 * from the net-value series, from which a snapshot can be opened, exported or
 * deleted.
 */
export class SnapshotListPage {
  constructor(private readonly page: Page) {}

  private get table() {
    return this.page.locator('[data-testid=snapshot-list-table]');
  }

  private row(timestamp: number) {
    return this.table.locator('tr', { has: this.page.locator(`[data-testid=snapshot-list-row][data-key="${timestamp}"]`) });
  }

  /** Opens the snapshot list, a submenu leaf under the Statistics group. */
  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'statistics', 'statistics-snapshots');
    await this.table.waitFor({ state: 'visible' });
  }

  /** The net worth the list shows for a snapshot, as rendered. */
  netWorth(timestamp: number) {
    return this.row(timestamp).locator('[data-testid=snapshot-list-value]');
  }

  async expectSnapshot(timestamp: number): Promise<void> {
    await expect(this.row(timestamp)).toBeVisible();
  }

  /**
   * @remarks
   * A delete refreshes the net-value series the list reads from, so the row goes some time after
   * the request returns.
   */
  async expectNoSnapshot(timestamp: number): Promise<void> {
    await expect(this.row(timestamp)).toHaveCount(0);
  }

  /**
   * Presses a row action from the keyboard. The task dock rises above a pagination bar resting near
   * the view's bottom, so until the page scrolls to its end, where the shell keeps room below the
   * content, it can cover the last row's actions; a click scrolls the row only into view, not clear
   * of the dock.
   */
  private async pressRowAction(timestamp: number, action: 'snapshot-open' | 'snapshot-delete'): Promise<void> {
    const button = this.row(timestamp).locator(`[data-testid=${action}]`);
    await button.focus();
    await this.page.keyboard.press('Enter');
  }

  async openEditor(timestamp: number): Promise<SnapshotEditorPage> {
    await this.pressRowAction(timestamp, 'snapshot-open');
    await this.page.waitForURL(/\/statistics\/snapshots\/\d+/);
    const editor = new SnapshotEditorPage(this.page);
    await editor.waitForLoaded();
    return editor;
  }

  async deleteSnapshot(timestamp: number): Promise<void> {
    await this.pressRowAction(timestamp, 'snapshot-delete');
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=button-confirm]').click();
    await this.row(timestamp).waitFor({ state: 'hidden' });
  }
}
