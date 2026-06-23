import type { Page } from '@playwright/test';
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
    return this.table.locator('tr', { has: this.page.locator(`[data-testid=snapshot-list-row-${timestamp}]`) });
  }

  async visit(): Promise<void> {
    // Snapshots is a submenu leaf under the Statistics group.
    await RotkiApp.navigateTo(this.page, 'statistics', 'statistics-snapshots');
    await this.table.waitFor({ state: 'visible' });
  }

  async hasSnapshot(timestamp: number): Promise<boolean> {
    return this.row(timestamp).isVisible();
  }

  async openEditor(timestamp: number): Promise<SnapshotEditorPage> {
    await this.row(timestamp).locator('[data-testid=snapshot-open]').click();
    await this.page.waitForURL(/\/statistics\/snapshots\/\d+/);
    const editor = new SnapshotEditorPage(this.page);
    await editor.waitForLoaded();
    return editor;
  }

  async deleteSnapshot(timestamp: number): Promise<void> {
    await this.row(timestamp).locator('[data-testid=snapshot-delete]').click();
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=button-confirm]').click();
    await this.row(timestamp).waitFor({ state: 'hidden' });
  }
}
