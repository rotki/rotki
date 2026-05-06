import type { Download, Page } from '@playwright/test';
import { EditSnapshotDialog } from './edit-snapshot-dialog';

export class ExportSnapshotDialog {
  constructor(private readonly page: Page) {}

  private get root() {
    return this.page.locator('[data-testid=export-snapshot-dialog]');
  }

  async waitForVisible(): Promise<void> {
    await this.root.waitFor({ state: 'visible' });
  }

  async openEdit(): Promise<EditSnapshotDialog> {
    await this.page.locator('[data-testid=export-snapshot-edit]').click();
    const dialog = new EditSnapshotDialog(this.page);
    await dialog.waitForVisible();
    return dialog;
  }

  async download(): Promise<Download> {
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.locator('[data-testid=export-snapshot-download]').click();
    return downloadPromise;
  }
}
