import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_LONG, TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

export class AssetsManagerPage {
  constructor(private readonly page: Page) {}

  async visit(submenu: string): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'asset-manager', submenu);
  }

  async openStatusFilter(): Promise<void> {
    await this.page.locator('[data-cy=status-filter]').scrollIntoViewIfNeeded();
    await this.page.locator('[data-cy=status-filter]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=status-filter]').click();
    await this.page.locator('[data-cy=asset-filter-menu]').waitFor({ state: 'attached' });
  }

  async closeStatusFilter(): Promise<void> {
    await this.page.locator('[data-cy=status-filter]').click();
    await this.page.locator('[data-cy=asset-filter-menu]').waitFor({ state: 'detached' });
  }

  async ignoredAssets(): Promise<string> {
    await this.openStatusFilter();
    const text = await this.page.locator('[data-cy=asset-filter-show_only]').textContent();
    await this.closeStatusFilter();
    return (text ?? '').replace(/[^\d.]/g, '');
  }

  async ignoredAssetCount(number: number): Promise<void> {
    await this.openStatusFilter();
    await expect(this.page.locator('[data-cy=asset-filter-show_only]')).toContainText(number.toString());
    await this.closeStatusFilter();
  }

  async visibleEntries(visible: number): Promise<void> {
    await expect(this.page.locator('[data-cy=managed-assets-table] tbody tr')).toHaveCount(visible);
  }

  async clearAllFilters(): Promise<void> {
    const maxIterations = 20;

    for (let i = 0; i < maxIterations; i++) {
      // Find filter chips by their accessible name pattern (e.g., "symbol = X" or "address = 0x...")
      const symbolChip = this.page.getByRole('button', { name: /^symbol = / });
      const addressChip = this.page.getByRole('button', { name: /^address = / });

      const symbolCount = await symbolChip.count();
      const addressCount = await addressChip.count();

      if (symbolCount === 0 && addressCount === 0)
        break;

      // Pick whichever chip exists
      const chip = symbolCount > 0 ? symbolChip.first() : addressChip.first();

      // Scroll chip into view and wait for it to be visible
      await chip.scrollIntoViewIfNeeded();
      await chip.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });

      // The close button is a nested button inside the chip
      const closeButton = chip.locator('button');
      await closeButton.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
      await closeButton.click();

      // Wait for chip to be removed
      await expect(chip).toBeHidden({ timeout: TIMEOUT_SHORT });

      // Wait for table to update
      await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
    }
  }

  async focusOnTableFilter(): Promise<void> {
    // Clear any existing filter chips first
    await this.clearAllFilters();

    // Wait for any pending table updates after clearing filters
    await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });

    const activator = this.page.locator('[data-cy=table-filter] [data-id=activator]');
    const arrowButton = activator.locator('> span:last-child');
    await arrowButton.click();
  }

  async searchAsset(asset: string): Promise<void> {
    await this.focusOnTableFilter();
    const input = this.page.locator('[data-cy=table-filter] input');
    await input.fill(`symbol: ${asset}`);
    await input.press('Enter');
    await input.press('Escape');

    // Wait for the filter chip to appear (confirms filter was applied)
    // The chip appears as a button containing text like "symbol = 1SG"
    const filterChip = this.page.getByRole('button', { name: `symbol = ${asset}` });
    await filterChip.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });

    // Wait for loader to detach (it may or may not appear)
    await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });

    // Poll until the results are filtered (pagination shows small total, not thousands)
    await expect(async () => {
      // Check pagination shows a small count (filtered results)
      const paginationText = await this.page.locator('[data-cy=managed-assets-table]').locator('text=/of \\d+/').first().textContent();
      const totalMatch = paginationText?.match(/of\s+(\d+)/);
      const total = totalMatch ? Number.parseInt(totalMatch[1]) : 0;
      // Filtered results should be less than 100
      expect(total).toBeLessThan(100);
      expect(total).toBeGreaterThan(0);
    }).toPass({ timeout: 30000 });
  }

  async findRowBySymbol(symbol: string): Promise<Locator> {
    const table = this.page.locator('[data-cy=managed-assets-table]');
    // Find the row that contains the exact symbol in the list-title element
    const row = table.locator('tbody tr').filter({
      has: this.page.locator('[data-cy=list-title]', { hasText: new RegExp(`^${symbol}$`) }),
    }).first();
    await expect(row).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    return row;
  }

  async searchAssetByAddress(address: string): Promise<void> {
    await this.focusOnTableFilter();
    const input = this.page.locator('[data-cy=table-filter] input');
    await input.fill(`address: ${address}`);
    await input.press('Enter');
    await input.press('Escape');
    await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached' });
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
    await this.page.locator('[data-cy=confirm-dialog]').locator('[data-cy=button-confirm]').click();
    // Wait for dialog to close and table to refresh
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'detached' });
  }

  async selectShowAll(): Promise<void> {
    await this.openStatusFilter();
    await this.page.locator('[data-cy=asset-filter-none]').scrollIntoViewIfNeeded();
    await this.page.locator('[data-cy=asset-filter-none]').click();
    await this.closeStatusFilter();
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
      this.page.locator('[data-cy=confirm-dialog]').locator('[data-cy=dialog-title]'),
    ).toContainText('Delete asset');

    const responsePromise = this.page.waitForResponse(
      response => response.url().includes('/api/1/assets/all') && response.request().method() === 'DELETE',
    );

    await this.page.locator('[data-cy=confirm-dialog]').locator('[data-cy=button-confirm]').click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'detached' });
  }

  async deleteAnEvmAsset(address: string): Promise<void> {
    await this.searchAssetByAddress(address);
    await this.page.locator('[data-cy=managed-assets-table] [data-cy=row-delete]').click();
    await this.confirmDelete();
  }

  async deleteOtherAsset(symbol: string): Promise<void> {
    await this.searchAsset(symbol);
    const row = await this.findRowBySymbol(symbol);
    await row.locator('[data-cy=row-delete]').click();
    await this.confirmDelete();
  }

  async showAddAssetModal(): Promise<void> {
    // Ensure any existing dialog is closed first
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    if (await dialog.isVisible()) {
      await this.page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'detached' });
    }

    const addButton = this.page.locator('[data-cy=managed-asset-add-btn]');
    await addButton.scrollIntoViewIfNeeded();
    await addButton.waitFor({ state: 'visible' });
    await addButton.click();
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await expect(this.page.locator('[data-cy=bottom-dialog] h5')).toContainText('Add a new asset');
  }

  async addAnEvmAsset(address: string, uniqueId: string): Promise<void> {
    // Open the add asset dialog
    await this.showAddAssetModal();

    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    const chainInput = dialog.locator('[data-cy=chain-select]');
    const tokenInput = dialog.locator('[data-cy=token-select]');
    const addressInput = dialog.locator('[data-cy=address-input] input');
    const nameInput = dialog.locator('[data-cy=name-input] input');
    const symbolInput = dialog.locator('[data-cy=symbol-input] input');
    const decimalInput = dialog.locator('[data-cy=decimal-input] input[type=number]');
    const submitButton = dialog.locator('[data-cy=confirm]');

    // Wait for form to be fully rendered
    await expect(chainInput).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    // Select a chain first
    await chainInput.click();
    const menuContent = this.page.locator('[role="menu-content"]');
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
    await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });

    // Search the asset
    await this.searchAssetByAddress(address);
    await expect(this.page.locator('[data-cy=managed-assets-table] [data-cy=list-title]')).toContainText(symbol);
  }

  async addOtherAsset(uniqueId: string): Promise<void> {
    // Open the add asset dialog
    await this.showAddAssetModal();

    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    const typeInput = dialog.locator('[data-cy=type-select]');
    const nameInput = dialog.locator('[data-cy=name-input] input');
    const symbolInput = dialog.locator('[data-cy=symbol-input] input');
    const submitButton = dialog.locator('[data-cy=confirm]');

    // Wait for form to be fully rendered
    await expect(typeInput).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    await typeInput.click();
    await this.page.locator('[role="menu-content"] button[type="button"]').filter({ hasText: 'Own chain' }).click();

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
    await this.page.locator('div[class*=thead__loader]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });

    // Search the asset
    await this.searchAsset(symbol);
    await expect(this.page.locator('[data-cy=managed-assets-table] [data-cy=list-title]')).toContainText(symbol);
  }

  async editEvmAsset(address: string, uniqueId: string): Promise<void> {
    await this.searchAssetByAddress(address);

    await this.page.locator('[data-cy=managed-assets-table] [data-cy=row-edit]').click();

    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
    await expect(this.page.locator('[data-cy=bottom-dialog] h5')).toContainText('Edit an asset');

    const symbolInput = this.page.locator('[data-cy=symbol-input] input');
    const submitButton = this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]');

    const symbol = `EDT${uniqueId}`;
    await symbolInput.clear();
    await symbolInput.fill(symbol);

    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached' });
    await expect(this.page.locator('[data-cy=managed-assets-table] [data-cy=list-title]')).toContainText(symbol);
  }
}
