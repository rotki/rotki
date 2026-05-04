import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

async function selectAsset(testId: string, asset: string, page: Page): Promise<void> {
  const select = page.getByTestId(testId);
  // RuiAutoComplete renders a zero-size input behind a clickable wrapper.
  // Click the wrapper to focus the typeahead, then type via keyboard.
  await select.click();
  await page.keyboard.type(asset);
  // Wait for the option list to populate, then commit via the menu item
  // matching the typed text exactly (case-insensitive identifier match).
  const menu = page.locator('[role="listbox"], [role="menu"]').last();
  await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
  const option = menu.locator(`#asset-${asset.toLowerCase()}`);
  await option.first().waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
  await option.first().click();
  await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_SHORT });
}

async function confirmDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-cy=bottom-dialog]');
  await dialog.locator('[data-cy=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-cy=confirm-dialog]');
  await confirmDialogEl.locator('[data-cy=button-confirm]').click();
  await confirmDialogEl.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function cancelDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-cy=bottom-dialog]');
  await dialog.locator('[data-cy=cancel]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

export class LatestPricePage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'price-manager', 'price-manager-latest');
  }

  private table() {
    return this.page.getByTestId('latest-price-table');
  }

  private rows() {
    return this.table().locator('tbody tr[data-id="row"]');
  }

  private rowMatching(value: string) {
    return this.rows().filter({ hasText: value });
  }

  async addPrice(fromAsset: string, toAsset: string, value: string): Promise<void> {
    await this.page.getByTestId('latest-price-add').click();
    await selectAsset('latest-price-from-asset', fromAsset, this.page);
    await selectAsset('latest-price-to-asset', toAsset, this.page);
    await this.page.getByTestId('latest-price-value').locator('input').fill(value);
    await confirmDialog(this.page);
  }

  async editPrice(currentValue: string, newValue: string): Promise<void> {
    await this.rowMatching(currentValue).first().locator('[data-cy=row-edit]').click();
    const valueInput = this.page.getByTestId('latest-price-value').locator('input');
    await valueInput.fill(newValue);
    await confirmDialog(this.page);
  }

  async deletePrice(value: string): Promise<void> {
    const row = this.rowMatching(value).first();
    await row.locator('[data-cy=row-delete]').click();
    await confirmDelete(this.page);
    await expect(this.rowMatching(value)).toHaveCount(0);
  }

  async expectRowWithValue(value: string): Promise<void> {
    await expect(this.rowMatching(value).first()).toBeVisible();
  }

  async expectVisibleRowCount(count: number): Promise<void> {
    await expect(this.rows()).toHaveCount(count);
  }

  async openAddDialog(): Promise<void> {
    await this.page.getByTestId('latest-price-add').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    await cancelDialog(this.page);
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await expect(dialog.getByText('The from asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The to asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The price cannot be empty')).toBeVisible();
  }

  async filterByFromAsset(asset: string): Promise<void> {
    await selectAsset('latest-price-filter-from', asset, this.page);
  }
}

export class HistoricPricePage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'price-manager', 'price-manager-historic');
  }

  private table() {
    return this.page.getByTestId('historic-price-table');
  }

  private rows() {
    return this.table().locator('tbody tr[data-id="row"]');
  }

  private rowMatching(value: string) {
    return this.rows().filter({ hasText: value });
  }

  async addPrice(fromAsset: string, toAsset: string, value: string, timestamp: string): Promise<void> {
    await this.page.getByTestId('historic-price-add').click();
    await selectAsset('historic-price-from-asset', fromAsset, this.page);
    await selectAsset('historic-price-to-asset', toAsset, this.page);
    const datetimeInput = this.page.getByTestId('historic-price-datetime').locator('input').first();
    await datetimeInput.click();
    await datetimeInput.fill(timestamp);
    // The datetime input opens a calendar popover on click; press Escape to dismiss
    // so the next form click is not intercepted by the calendar overlay.
    await this.page.keyboard.press('Escape');
    await this.page.getByTestId('historic-price-value').locator('input').fill(value);
    await confirmDialog(this.page);
  }

  async editPrice(currentValue: string, newValue: string): Promise<void> {
    await this.rowMatching(currentValue).first().locator('[data-cy=row-edit]').click();
    const valueInput = this.page.getByTestId('historic-price-value').locator('input');
    await valueInput.fill(newValue);
    await confirmDialog(this.page);
  }

  async deletePrice(value: string): Promise<void> {
    const row = this.rowMatching(value).first();
    await row.locator('[data-cy=row-delete]').click();
    await confirmDelete(this.page);
    await expect(this.rowMatching(value)).toHaveCount(0);
  }

  async expectRowWithValue(value: string): Promise<void> {
    await expect(this.rowMatching(value).first()).toBeVisible();
  }

  async expectVisibleRowCount(count: number): Promise<void> {
    await expect(this.rows()).toHaveCount(count);
  }

  async openAddDialog(): Promise<void> {
    await this.page.getByTestId('historic-price-add').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    await cancelDialog(this.page);
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await expect(dialog.getByText('The from asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The to asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The price cannot be empty')).toBeVisible();
  }

  async filterByFromAsset(asset: string): Promise<void> {
    await selectAsset('historic-price-filter-from', asset, this.page);
  }
}

export class OraclePricePage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'price-manager', 'price-manager-oracle');
  }

  async expectTableVisible(): Promise<void> {
    await expect(this.page.getByTestId('oracle-price-table')).toBeVisible();
  }
}
