import type { Page } from '@playwright/test';
import path from 'node:path';
import { TIMEOUT_LONG } from '../helpers/constants';
import { dismissNotificationPopups } from '../helpers/notifications';
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
    const select = this.page.locator('[data-testid=import-source-select]');
    await select.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=listbox]').last();
    await menu.waitFor({ state: 'visible' });
    await select.locator('input').fill(label);
    const option = menu.getByText(label, { exact: false }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
  }

  async uploadFile(sourceKey: string, csvFileName: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    const fileInput = container.locator('[data-id=file-input]');
    const filePath = path.resolve(BACKEND_TEST_DATA, csvFileName);
    await fileInput.setInputFiles(filePath);
  }

  /** Unfolds a source's parsing options, which start folded, unless they are already open. */
  async openParsingOptions(sourceKey: string): Promise<void> {
    const toggle = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`).getByTestId('import-options-toggle');
    if (await toggle.getAttribute('aria-expanded') !== 'true')
      await toggle.click();
  }

  async selectTimezone(sourceKey: string, timezone: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    await this.openParsingOptions(sourceKey);
    await container.getByTestId('import-timezone-switch').locator('input').click();
    const select = container.getByTestId('import-timezone-select');
    await select.waitFor({ state: 'visible' });
    await select.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=listbox]').last();
    await menu.waitFor({ state: 'visible' });
    await select.locator('input').fill(timezone);
    const option = menu.getByText(timezone, { exact: true }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
  }

  async submitImport(sourceKey: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    await container.locator('[data-testid=button-import]').click();
  }

  async waitForImportComplete(sourceKey: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    await container.locator('[data-testid=import-complete]').waitFor({ state: 'visible', timeout: TIMEOUT_LONG });
  }

  async dismissNotifications(): Promise<void> {
    await dismissNotificationPopups(this.page);
  }

  async importCsv(sourceKey: string, csvFileName: string): Promise<void> {
    await this.uploadFile(sourceKey, csvFileName);
    await this.submitImport(sourceKey);
    await this.waitForImportComplete(sourceKey);
    await this.dismissNotifications();
  }
}
