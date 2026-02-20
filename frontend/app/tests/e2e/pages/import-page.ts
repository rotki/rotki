import type { Page } from '@playwright/test';
import path from 'node:path';
import { TIMEOUT_LONG } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

/**
 * Path to shared backend test data directory.
 * CSV fixtures live here — no need to duplicate them in the frontend.
 */
const BACKEND_TEST_DATA = path.resolve(import.meta.dirname, '..', '..', '..', '..', '..', 'rotkehlchen', 'tests', 'data');

export class ImportPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'import');
  }

  async selectSource(label: string): Promise<void> {
    const select = this.page.locator('[data-cy=import-source-select]');
    await select.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    await select.locator('input').fill(label);
    const option = menu.getByText(label, { exact: false }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
  }

  async uploadFile(sourceKey: string, csvFileName: string): Promise<void> {
    const container = this.page.locator(`[data-cy="import-source-${sourceKey}"]`);
    const fileInput = container.locator('[data-cy=file-input]');
    const filePath = path.resolve(BACKEND_TEST_DATA, csvFileName);
    await fileInput.setInputFiles(filePath);
  }

  async submitImport(sourceKey: string): Promise<void> {
    const container = this.page.locator(`[data-cy="import-source-${sourceKey}"]`);
    await container.locator('[data-cy=button-import]').click();
  }

  async waitForImportComplete(sourceKey: string): Promise<void> {
    const container = this.page.locator(`[data-cy="import-source-${sourceKey}"]`);
    await container.locator('[data-cy=import-complete]').waitFor({ state: 'visible', timeout: TIMEOUT_LONG });
  }

  async dismissNotifications(): Promise<void> {
    const dismissButton = this.page.locator('[data-id=notification_dismiss]');
    if (await dismissButton.isVisible()) {
      await dismissButton.click();
      await this.page.locator('[data-id=notification]').waitFor({ state: 'detached' });
    }
  }

  async importCsv(sourceKey: string, csvFileName: string): Promise<void> {
    await this.uploadFile(sourceKey, csvFileName);
    await this.submitImport(sourceKey);
    await this.waitForImportComplete(sourceKey);
    await this.dismissNotifications();
  }
}
