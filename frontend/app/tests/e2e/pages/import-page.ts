import type { Locator, Page } from '@playwright/test';
import path from 'node:path';
import { TIMEOUT_LONG } from '../helpers/constants';
import { selectLocationOption } from './location-manager-page';
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

  locationMappingDialog(): Locator {
    return this.page.locator('[data-testid=bottom-dialog]').filter({ has: this.page.getByTestId('import-location-mapping') });
  }

  /** The location values of the file the mapping dialog asks about, in the order it lists them. */
  async unresolvedLocationValues(): Promise<string[]> {
    const dialog = this.locationMappingDialog();
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_LONG });
    const values = dialog.getByTestId('import-location-value');
    const result: string[] = [];
    for (let index = 0; index < await values.count(); index++)
      result.push(await values.nth(index).getAttribute('data-value') ?? '');
    return result;
  }

  /** Maps one location value of the file to a location, leaving "save as aliases" as it is. */
  async mapLocationValue(value: string, locationName: string, locationIdentifier: string): Promise<void> {
    await selectLocationOption(this.page, this.locationChoice(value), locationName, locationIdentifier);
  }

  private locationChoice(value: string): Locator {
    return this.locationMappingDialog()
      .locator(`[data-testid=import-location-value][data-value="${value}"]`)
      .getByTestId('import-location-choice');
  }

  /** The identifiers of the locations offered for one value of the file. */
  async locationChoiceOptions(value: string): Promise<string[]> {
    await this.locationChoice(value).locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    const ids = await menu.locator('[id^="balance-location__"]').evaluateAll(items => items.map(item => item.id));
    await this.page.keyboard.press('Escape');
    await menu.waitFor({ state: 'hidden' });
    return ids.map(id => id.replace('balance-location__', ''));
  }

  /** The name the choice for a value shows once a location is picked for it. */
  locationChoiceSelection(value: string): Locator {
    return this.locationChoice(value).getByTestId('location-selection');
  }

  /** Opens the location form for a value, prefilled with it, on top of the mapping dialog. */
  async createLocationFor(value: string): Promise<void> {
    await this.locationMappingDialog()
      .locator(`[data-testid=import-location-value][data-value="${value}"]`)
      .getByTestId('import-location-create')
      .click();
  }

  async confirmLocationMapping(): Promise<void> {
    await this.locationMappingDialog().getByTestId('confirm').click();
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
