import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { PillFilterBar } from './pill-filter-bar';
import { RotkiApp } from './rotki-app';

/**
 * How to recognise the wanted option once the typeahead has answered.
 *
 * A symbol carries a stable option id, so `id` names the exact entry. A custom asset's id is a
 * UUID the spec never sees, so `name` matches on the text instead.
 */
export type AssetMatch = 'id' | 'name';

/**
 * Picks an asset out of a RuiAutoComplete typeahead.
 *
 * @remarks
 * AssetSelect debounces its search (~800ms), so the option has to be waited for rather than read
 * off whatever the menu is showing at click time. The caller says which kind of asset it is asking
 * for: choosing between the two by racing a timeout would let a slow search downgrade a symbol
 * lookup into "click whatever rendered", and the test would go on asserting about the wrong asset.
 *
 * @param testId - the select's `data-testid`
 * @param asset - a symbol for `id`, the asset's name for `name`
 * @param page - the page holding the select
 * @param match - which of the two the caller is passing
 */
async function selectAsset(testId: string, asset: string, page: Page, match: AssetMatch = 'id'): Promise<void> {
  const select = page.getByTestId(testId);
  // A previously selected chip would block the new typeahead query.
  const clearButton = select.locator('[data-id=clear]');
  if ((await clearButton.count()) > 0)
    await clearButton.first().click();
  // RuiAutoComplete hides a zero-size input behind the wrapper, so the wrapper takes the click.
  await select.click();
  await page.keyboard.type(asset);
  const menu = page.locator('[role="listbox"], [role="menu"]').last();
  await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
  const option = match === 'id'
    ? menu.locator(`#asset-${asset.toLowerCase()}`).first()
    : menu.locator('button[type="button"]').filter({ hasText: asset }).first();
  await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  await option.click();
  await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_SHORT });
}

async function confirmDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-testid=bottom-dialog]');
  await dialog.locator('[data-testid=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-testid=confirm-dialog]');
  await confirmDialogEl.locator('[data-testid=button-confirm]').click();
  await confirmDialogEl.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function cancelDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-testid=bottom-dialog]');
  await dialog.locator('[data-testid=cancel]').click();
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

  /**
   * Adds a latest price.
   *
   * @remarks
   * `fromMatch` is `name` when `fromAsset` is a custom asset, whose id is a UUID the spec never
   * sees. The `to` asset is always a symbol.
   */
  async addPrice(fromAsset: string, toAsset: string, value: string, fromMatch: AssetMatch = 'id'): Promise<void> {
    await this.page.getByTestId('latest-price-add').click();
    await selectAsset('latest-price-from-asset', fromAsset, this.page, fromMatch);
    await selectAsset('latest-price-to-asset', toAsset, this.page);
    await this.page.getByTestId('latest-price-value').locator('input').fill(value);
    await confirmDialog(this.page);
  }

  async editPrice(currentValue: string, newValue: string): Promise<void> {
    await this.rowMatching(currentValue).first().locator('[data-testid=row-edit]').click();
    const valueInput = this.page.getByTestId('latest-price-value').locator('input');
    await valueInput.fill(newValue);
    await confirmDialog(this.page);
  }

  async deletePrice(value: string): Promise<void> {
    const row = this.rowMatching(value).first();
    await row.locator('[data-testid=row-delete]').click();
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
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    await cancelDialog(this.page);
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
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
    // The calendar popover opens on click and would intercept the next form click.
    await this.page.keyboard.press('Escape');
    await this.page.getByTestId('historic-price-value').locator('input').fill(value);
    await confirmDialog(this.page);
  }

  async editPrice(currentValue: string, newValue: string): Promise<void> {
    await this.rowMatching(currentValue).first().locator('[data-testid=row-edit]').click();
    const valueInput = this.page.getByTestId('historic-price-value').locator('input');
    await valueInput.fill(newValue);
    await confirmDialog(this.page);
  }

  async deletePrice(value: string): Promise<void> {
    const row = this.rowMatching(value).first();
    await row.locator('[data-testid=row-delete]').click();
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
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    await cancelDialog(this.page);
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await expect(dialog.getByText('The from asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The to asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The price cannot be empty')).toBeVisible();
  }

  /** Narrows by the from-asset through the pill bar, which replaced the two asset selects. */
  async filterByFromAsset(asset: string): Promise<void> {
    const bar = new PillFilterBar(this.page);

    if (await bar.pill('fromAsset').count() === 0)
      await bar.addField('fromAsset');
    else
      await bar.openPillEditor('fromAsset');

    await bar.selectValue(asset, asset);
    await bar.closeEditor('fromAsset');
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
