import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_LONG, TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { PillFilterBar } from './pill-filter-bar';
import { RotkiApp } from './rotki-app';

/** The ignored-handling pill's field key, and the value that shows ignored assets alongside the rest. */
const IGNORED_FIELD = 'ignored';
const SHOW_ALL = 'none';
const ONLY_IGNORED = 'show_only';

export class AssetsManagerPage {
  private readonly pill: PillFilterBar;

  constructor(private readonly page: Page) {
    this.pill = new PillFilterBar(page);
  }

  async visit(submenu: string): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'asset-manager', submenu);
  }

  /**
   * Opens the ignored-handling pill's value list, adding the pill first when it is not there yet.
   *
   * Reading the ignored count means reading the "only ignored" option's own label, which is where
   * the count lives now that the status dropdown is gone. A pill added just to read it carries no
   * value, so closing the editor drops it again.
   */
  private async openIgnoredValues(): Promise<void> {
    if (await this.pill.pill(IGNORED_FIELD).count() > 0)
      await this.pill.openPillEditor(IGNORED_FIELD);
    else
      await this.pill.addField(IGNORED_FIELD);

    await this.page
      .locator(`[data-testid=value-select-option][data-key="${ONLY_IGNORED}"]`)
      .waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async ignoredAssets(): Promise<string> {
    await this.openIgnoredValues();
    const text = await this.page.locator(`[data-testid=value-select-option][data-key="${ONLY_IGNORED}"]`).textContent();
    await this.pill.closeEditor(IGNORED_FIELD);
    return (text ?? '').replace(/[^\d.]/g, '');
  }

  async ignoredAssetCount(number: number): Promise<void> {
    await this.openIgnoredValues();
    await expect(
      this.page.locator(`[data-testid=value-select-option][data-key="${ONLY_IGNORED}"]`),
    ).toContainText(number.toString(), { timeout: TIMEOUT_MEDIUM });
    await this.pill.closeEditor(IGNORED_FIELD);
  }

  async visibleEntries(visible: number): Promise<void> {
    await expect(this.page.locator('[data-testid=managed-assets-table] tbody tr')).toHaveCount(visible);
  }

  /**
   * Drops every pill except the ones named.
   *
   * The ignored handling is a pill of its own now, and a test that says "show ignored assets too"
   * then filters to one symbol means both at once — clearing the bar wholesale would silently put
   * ignored assets back out of sight.
   */
  private async clearFiltersExcept(keep: string[]): Promise<void> {
    const fields = await this.page.locator('[data-testid=filter-pill]').evaluateAll(pills =>
      pills.map(pill => pill.getAttribute('data-field')).filter((field): field is string => field !== null));

    for (const field of fields.filter(field => !keep.includes(field))) {
      await this.pill.removePill(field);
      await this.pill.expectNoPill(field);
    }

    await expect(this.page.locator('[data-id="thead-loader"]')).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Filters to one asset by a free-text field (symbol, address), replacing whatever was filtered
   * before but leaving the ignored handling as the test set it.
   */
  private async filterBy(fieldKey: string, value: string): Promise<void> {
    await this.clearFiltersExcept([IGNORED_FIELD]);
    await this.pill.addField(fieldKey);
    await this.pill.typeTextValue(value);
    await this.pill.closeEditor(fieldKey);
    await this.pill.expectPillVisible(fieldKey);
    await expect(this.page.locator('[data-id="thead-loader"]')).toHaveCount(0, { timeout: TIMEOUT_LONG });
  }

  async searchAsset(asset: string): Promise<void> {
    await this.filterBy('symbol', asset);

    // Poll until the results are filtered (pagination shows a small total, not thousands)
    await expect(async () => {
      const paginationText = await this.page.locator('[data-testid=managed-assets-table]').locator('text=/of \\d+/').first().textContent();
      const totalMatch = paginationText?.match(/of\s+(\d+)/);
      const total = totalMatch ? Number.parseInt(totalMatch[1]) : 0;
      expect(total).toBeLessThan(100);
      expect(total).toBeGreaterThan(0);
    }).toPass({ timeout: 30000 });
  }

  async findRowBySymbol(symbol: string): Promise<Locator> {
    const table = this.page.locator('[data-testid=managed-assets-table]');
    // Find the row that contains the exact symbol in the list-title element
    const row = table.locator('tbody tr').filter({
      has: this.page.locator('[data-testid=list-title]', { hasText: new RegExp(`^${symbol}$`) }),
    }).first();
    await expect(row).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    return row;
  }

  async searchAssetByAddress(address: string): Promise<void> {
    await this.filterBy('address', address);
    await this.visibleEntries(1);
  }

  async addIgnoredAsset(asset: string): Promise<void> {
    await this.searchAsset(asset);
    const row = await this.findRowBySymbol(asset);

    const switchInput = row.locator('td:nth-child(6) input');
    // Wait for the switch to be enabled (not loading)
    await expect(switchInput).toBeEnabled();
    const isChecked = await switchInput.isChecked();
    expect(isChecked).toBe(false);

    await switchInput.click();
    await expect(switchInput).toBeChecked();
    await this.page.locator('[data-testid=confirm-dialog]').locator('[data-testid=button-confirm]').click();
    // Wait for dialog to close and table to refresh
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'detached' });
  }

  /**
   * Shows ignored assets alongside the rest. Idempotent: the pill survives between tests in a
   * serial group, and re-picking a value it already holds would toggle it back off.
   */
  async selectShowAll(): Promise<void> {
    await this.openIgnoredValues();
    // Clicked directly rather than through the bar's search box: the box narrows on an option's
    // label, and this list is two entries long, so searching would only risk hiding the one wanted.
    const option = this.page.locator(`[data-testid=value-select-option][data-key="${SHOW_ALL}"]`);
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    if (await option.getAttribute('aria-checked') !== 'true')
      await option.click();
    await this.pill.closeEditor(IGNORED_FIELD);
    await this.pill.expectPillVisible(IGNORED_FIELD);
    await expect(this.page.locator('[data-id="thead-loader"]')).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  async removeIgnoredAsset(asset: string): Promise<void> {
    await this.searchAsset(asset);
    const row = await this.findRowBySymbol(asset);

    const switchInput = row.locator('td:nth-child(6) input');
    // Wait for the switch to be enabled (not loading)
    await expect(switchInput).toBeEnabled();
    const isChecked = await switchInput.isChecked();
    expect(isChecked).toBe(true);

    await switchInput.click();
    await expect(switchInput).not.toBeChecked();
  }

  async confirmDelete(): Promise<void> {
    await expect(
      this.page.locator('[data-testid=confirm-dialog]').locator('[data-testid=dialog-title]'),
    ).toContainText('Delete asset');

    const responsePromise = this.page.waitForResponse(
      response => response.url().includes('/api/1/assets/all') && response.request().method() === 'DELETE',
    );

    await this.page.locator('[data-testid=confirm-dialog]').locator('[data-testid=button-confirm]').click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'detached' });
  }

  async deleteAnEvmAsset(address: string): Promise<void> {
    await this.searchAssetByAddress(address);
    await this.page.locator('[data-testid=managed-assets-table] [data-testid=row-delete]').click();
    await this.confirmDelete();
  }

  async deleteOtherAsset(symbol: string): Promise<void> {
    await this.searchAsset(symbol);
    const row = await this.findRowBySymbol(symbol);
    await row.locator('[data-testid=row-delete]').click();
    await this.confirmDelete();
  }

  async showAddAssetModal(): Promise<void> {
    // Ensure any existing dialog is closed first
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    if (await dialog.isVisible()) {
      await this.page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'detached' });
    }

    const addButton = this.page.locator('[data-testid=managed-asset-add-btn]');
    await addButton.scrollIntoViewIfNeeded();
    await addButton.waitFor({ state: 'visible' });
    await addButton.click();
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await expect(this.page.locator('[data-testid=bottom-dialog] h5')).toContainText('Add a new asset');
  }

  async addAnEvmAsset(address: string, uniqueId: string): Promise<void> {
    // Open the add asset dialog
    await this.showAddAssetModal();

    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    const chainInput = dialog.locator('[data-testid=chain-select]');
    const tokenInput = dialog.locator('[data-testid=token-select]');
    const addressInput = dialog.locator('[data-testid=address-input] input');
    const nameInput = dialog.locator('[data-testid=name-input] input');
    const symbolInput = dialog.locator('[data-testid=symbol-input] input');
    const decimalInput = dialog.locator('[data-testid=decimal-input] input[type=number]');
    const submitButton = dialog.locator('[data-testid=confirm]');

    // Wait for form to be fully rendered
    await expect(chainInput).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    // Select a chain first
    await chainInput.click();
    const menuContent = this.page.locator('[role="menu"]');
    await expect(menuContent).toBeVisible({ timeout: TIMEOUT_SHORT });
    await menuContent.locator('button[type="button"]').first().click();

    // Select a token type
    await tokenInput.click();
    await expect(menuContent).toBeVisible({ timeout: TIMEOUT_SHORT });
    await menuContent.locator('button[type="button"]').first().click();

    // Enter address
    await addressInput.fill(address);

    // Enter name with unique ID
    await nameInput.clear();
    await nameInput.fill(`ASSET NAME ${uniqueId}`);

    const symbol = `SYM${uniqueId}`;
    // Enter symbol with unique ID
    await symbolInput.clear();
    await symbolInput.fill(symbol);

    // Enter decimals
    await decimalInput.clear();
    await decimalInput.fill('2');

    // Submit the form
    await expect(submitButton).toBeEnabled();
    await submitButton.click();
    await dialog.waitFor({ state: 'detached' });

    // Refresh the table to ensure the new asset appears
    await this.page.locator('button', { hasText: 'Refresh' }).first().click();
    await expect(this.page.locator('[data-id="thead-loader"]')).toHaveCount(0, { timeout: TIMEOUT_LONG });

    // Search the asset
    await this.searchAssetByAddress(address);
    await expect(this.page.locator('[data-testid=managed-assets-table] [data-testid=list-title]')).toContainText(symbol);
  }

  async addOtherAsset(uniqueId: string): Promise<void> {
    // Open the add asset dialog
    await this.showAddAssetModal();

    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    const typeInput = dialog.locator('[data-testid=type-select]');
    const nameInput = dialog.locator('[data-testid=name-input] input');
    const symbolInput = dialog.locator('[data-testid=symbol-input] input');
    const submitButton = dialog.locator('[data-testid=confirm]');

    // Wait for form to be fully rendered
    await expect(typeInput).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    await typeInput.click();
    await this.page.locator('[role="menu"] button[type="button"]').filter({ hasText: 'Own chain' }).click();

    await nameInput.clear();
    await nameInput.fill(`NAME ${uniqueId}`);

    const symbol = `OTH${uniqueId}`;
    await symbolInput.clear();
    await symbolInput.fill(symbol);

    await expect(submitButton).toBeEnabled();
    await submitButton.click();
    await dialog.waitFor({ state: 'detached' });

    // Refresh the table to ensure the new asset appears
    await this.page.locator('button', { hasText: 'Refresh' }).first().click();
    await expect(this.page.locator('[data-id="thead-loader"]')).toHaveCount(0, { timeout: TIMEOUT_LONG });

    // Search the asset
    await this.searchAsset(symbol);
    await expect(this.page.locator('[data-testid=managed-assets-table] [data-testid=list-title]')).toContainText(symbol);
  }

  async editEvmAsset(address: string, uniqueId: string): Promise<void> {
    await this.searchAssetByAddress(address);

    await this.page.locator('[data-testid=managed-assets-table] [data-testid=row-edit]').click();

    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
    await expect(this.page.locator('[data-testid=bottom-dialog] h5')).toContainText('Edit an asset');

    const symbolInput = this.page.locator('[data-testid=symbol-input] input');
    const submitButton = this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]');

    const symbol = `EDT${uniqueId}`;
    await symbolInput.clear();
    await symbolInput.fill(symbol);

    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'detached' });
    await expect(this.page.locator('[data-testid=managed-assets-table] [data-testid=list-title]')).toContainText(symbol);
  }
}
