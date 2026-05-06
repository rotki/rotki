import type { Page } from '@playwright/test';

export class SnapshotImportDialog {
  constructor(private readonly page: Page) {}

  private get root() {
    return this.page.locator('[data-testid=snapshot-import-dialog]');
  }

  async waitForVisible(): Promise<void> {
    await this.root.waitFor({ state: 'visible' });
  }

  async uploadBalanceCsv(filePath: string): Promise<void> {
    await this.root
      .locator('[data-testid=snapshot-import-balance-file] input[type=file]')
      .setInputFiles(filePath);
  }

  async uploadLocationCsv(filePath: string): Promise<void> {
    await this.root
      .locator('[data-testid=snapshot-import-location-file] input[type=file]')
      .setInputFiles(filePath);
  }

  async import(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-import-submit]').click();
  }
}
