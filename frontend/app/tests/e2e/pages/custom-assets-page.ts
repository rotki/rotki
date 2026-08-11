import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

export class CustomAssetsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'asset-manager', 'asset-manager-custom');
    await expect(this.page.locator('[data-testid=custom-assets-table]')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  private rowFor(name: string): Locator {
    return this.page.locator('[data-testid=custom-assets-table] tbody tr[data-id="row"]').filter({ hasText: name });
  }

  async addAsset(opts: { name: string; type: string; notes?: string }): Promise<void> {
    await this.openDialog();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.locator('[data-testid=name] input').fill(opts.name);
    // Custom asset type uses an autocomplete that also accepts free-text values.
    const typeInput = dialog.locator('[data-testid=type] input').first();
    await typeInput.click();
    await typeInput.fill(opts.type);
    // Press Enter to commit the free-text value through the autocomplete.
    await typeInput.press('Enter');
    if (opts.notes !== undefined) {
      await dialog.locator('[data-testid=notes] textarea:not([readonly])').fill(opts.notes);
    }
    await this.submitDialog();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async editAsset(name: string, opts: { newName?: string; newNotes?: string }): Promise<void> {
    await this.rowFor(name).first().locator('[data-testid=row-edit]').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    if (opts.newName !== undefined) {
      const nameInput = dialog.locator('[data-testid=name] input');
      await nameInput.click({ clickCount: 3 });
      await nameInput.fill(opts.newName);
    }
    if (opts.newNotes !== undefined) {
      await dialog.locator('[data-testid=notes] textarea:not([readonly])').fill(opts.newNotes);
    }
    await this.submitDialog();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async deleteAsset(name: string): Promise<void> {
    await this.rowFor(name).first().locator('[data-testid=row-delete]').click();
    const confirmDialog = this.page.locator('[data-testid=confirm-dialog]');
    await confirmDialog.locator('[data-testid=button-confirm]').click();
    await confirmDialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async expectRow(name: string): Promise<void> {
    await expect(this.rowFor(name).first()).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectNoRow(name: string): Promise<void> {
    await expect(this.rowFor(name)).toHaveCount(0);
  }

  async openDialog(): Promise<void> {
    await this.page.locator('[data-testid=managed-asset-add-btn]').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.locator('[data-testid=cancel]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await expect(dialog.getByText('The name of the asset cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The type of the asset cannot be empty')).toBeVisible();
  }
}
