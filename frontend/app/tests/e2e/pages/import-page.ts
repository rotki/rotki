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
    const select = this.page.locator('[data-testid=import-source-select]');
    await select.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    await select.locator('input').fill(label);
    const option = menu.getByText(label, { exact: false }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
  }

  async uploadFile(sourceKey: string, csvFileName: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    const fileInput = container.locator('[data-testid=file-input]');
    const filePath = path.resolve(BACKEND_TEST_DATA, csvFileName);
    await fileInput.setInputFiles(filePath);
  }

  async selectTimezone(sourceKey: string, timezone: string): Promise<void> {
    const container = this.page.locator(`[data-testid=import-source][data-key="${sourceKey}"]`);
    await container.getByTestId('import-timezone-switch').locator('input').click();
    const select = container.getByTestId('import-timezone-select');
    await select.waitFor({ state: 'visible' });
    await select.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
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
    const dismissButton = this.page.locator('[data-id=notification_dismiss]');
    if (await dismissButton.isVisible()) {
      await dismissButton.click();
      await this.page.locator('[data-id=notification]').waitFor({ state: 'detached' });
    }
  }

  /**
   * Maps every location value the import could not resolve to the given location, then imports.
   *
   * @remarks
   * Only rotki's own formats ask: their rows name a location, and a value the app does not know
   * has to be mapped before anything is imported.
   */
  async mapUnknownLocations(locationName: string): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]').filter({ has: this.page.getByTestId('import-location-mapping') });
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_LONG });
    const choices = dialog.getByTestId('import-location-choice');
    for (let index = 0; index < await choices.count(); index++) {
      const choice = choices.nth(index);
      await choice.locator('[data-id=activator]').click();
      const menu = this.page.locator('[role=menu]').last();
      await menu.waitFor({ state: 'visible' });
      await choice.locator('input').fill(locationName);
      const option = menu.getByText(locationName, { exact: false }).first();
      await option.waitFor({ state: 'visible' });
      await option.click();
      await menu.waitFor({ state: 'hidden' });
    }
    await dialog.getByTestId('import-location-save-aliases').locator('input').uncheck();
    await dialog.getByTestId('confirm').click();
  }

  async importCsv(sourceKey: string, csvFileName: string, unknownLocationsTo?: string): Promise<void> {
    await this.uploadFile(sourceKey, csvFileName);
    await this.submitImport(sourceKey);
    if (unknownLocationsTo)
      await this.mapUnknownLocations(unknownLocationsTo);
    await this.waitForImportComplete(sourceKey);
    await this.dismissNotifications();
  }
}
