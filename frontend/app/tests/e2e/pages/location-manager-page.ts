import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

/**
 * Picks a location in a `LocationSelector`.
 *
 * @remarks
 * The option is found by its identifier: names repeat across branches and an option also prints
 * its parent path, so matching on text can land on a different location that mentions the name.
 */
export async function selectLocationOption(page: Page, field: Locator, name: string, identifier: string): Promise<void> {
  await field.locator('[data-id=activator]').click();
  const menu = page.locator('[role=menu]').last();
  await menu.waitFor({ state: 'visible' });
  await field.locator('input').fill(name);
  const option = menu.locator(`[id="balance-location__${identifier}"]`);
  await option.waitFor({ state: 'visible' });
  await option.click();
  await menu.waitFor({ state: 'hidden' });
}

export class LocationManagerPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'location-manager');
    await this.table().waitFor({ state: 'visible' });
  }

  private table(): Locator {
    return this.page.getByTestId('location-manager-table');
  }

  /**
   * The last dialog holding a location form: the import mapping dialog opens the form on top of
   * itself, and the outer dialog would match too.
   */
  private formDialog(): Locator {
    return this.page.locator('[data-testid=bottom-dialog]').filter({ has: this.page.getByTestId('location-form') }).last();
  }

  /** The table row of a location, found by its identifier. */
  row(identifier: string): Locator {
    return this.table().locator('tbody tr').filter({ has: this.page.locator(`[data-location="${identifier}"]`) });
  }

  /** The names of the listed rows, in the order the tree shows them. */
  rowNames(): Locator {
    return this.table().getByTestId('location-row-name');
  }

  async openTab(tab: 'locations' | 'aliases'): Promise<void> {
    await this.page.getByTestId('location-manager-tabs').getByRole('tab', { name: tab === 'aliases' ? 'Aliases' : 'Locations' }).click();
  }

  async search(term: string): Promise<void> {
    await this.page.getByTestId('location-manager-search').locator('input').fill(term);
  }

  async setShowArchived(show: boolean): Promise<void> {
    const toggle = this.page.getByTestId('location-manager-show-archived').locator('input');
    if (await toggle.isChecked() !== show)
      await toggle.click();
  }

  async addChildOf(parentIdentifier: string): Promise<void> {
    await this.row(parentIdentifier).getByTestId('location-add-child').click();
    await this.formDialog().waitFor({ state: 'visible' });
  }

  async createFromSearch(): Promise<void> {
    await this.page.getByTestId('location-manager-create-from-search').click();
    await this.formDialog().waitFor({ state: 'visible' });
  }

  async edit(identifier: string): Promise<void> {
    await this.row(identifier).getByTestId('row-edit').click();
    await this.formDialog().waitFor({ state: 'visible' });
  }

  async requestDelete(identifier: string): Promise<void> {
    await this.row(identifier).getByTestId('row-delete').click();
  }

  formName(): Locator {
    return this.formDialog().getByTestId('location-form-name').locator('input');
  }

  async fillName(name: string): Promise<void> {
    await this.formName().fill(name);
  }

  async selectParent(name: string, identifier: string): Promise<void> {
    await selectLocationOption(this.page, this.formDialog().getByTestId('location-form-parent'), name, identifier);
  }

  async waitForForm(): Promise<void> {
    await this.formDialog().waitFor({ state: 'visible' });
  }

  async chooseImage(filePath: string): Promise<void> {
    await this.formDialog().getByTestId('location-image-input').setInputFiles(filePath);
    await expect(this.formDialog().getByTestId('location-image-preview')).toBeVisible();
  }

  async removeImage(): Promise<void> {
    await this.formDialog().getByTestId('location-image-remove').click();
    await expect(this.formDialog().getByTestId('location-image-preview')).toHaveCount(0);
  }

  async saveForm(): Promise<void> {
    await this.formDialog().getByTestId('confirm').click();
  }

  async cancelForm(): Promise<void> {
    await this.formDialog().getByTestId('cancel').click();
  }

  async expectFormClosed(): Promise<void> {
    await expect(this.formDialog()).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  confirmDialog(): Locator {
    return this.page.getByTestId('confirm-dialog');
  }

  async confirm(): Promise<void> {
    await this.confirmDialog().getByTestId('button-confirm').click();
    await this.confirmDialog().waitFor({ state: 'detached' });
  }

  usageDialog(): Locator {
    return this.page.getByTestId('location-usage-dialog');
  }

  async closeUsage(): Promise<void> {
    await this.usageDialog().getByRole('button', { name: 'Close' }).click();
    await this.usageDialog().waitFor({ state: 'detached' });
  }

  async openUsageLink(label: string): Promise<void> {
    await this.usageDialog().getByTestId('location-usage-link').filter({ hasText: label }).click();
    await this.usageDialog().waitFor({ state: 'detached' });
  }

  async toggleArchive(identifier: string): Promise<void> {
    await this.row(identifier).getByTestId('location-toggle-archive').click();
  }

  async deleteAlias(alias: string): Promise<void> {
    await this.aliasRow(alias).getByTestId('location-alias-delete').click();
    await this.confirm();
  }

  async archiveFromUsage(): Promise<void> {
    await this.usageDialog().getByTestId('location-usage-archive').click();
    await this.usageDialog().waitFor({ state: 'detached' });
  }

  async addAlias(alias: string, name: string, identifier: string): Promise<void> {
    const form = this.page.getByTestId('location-alias-form');
    await form.getByTestId('location-alias-name').locator('input').fill(alias);
    await selectLocationOption(this.page, form.getByTestId('location-alias-target'), name, identifier);
    await form.getByTestId('location-alias-save').click();
  }

  aliasRow(alias: string): Locator {
    return this.page.getByTestId('location-aliases-table').locator('tbody tr').filter({ has: this.page.getByText(alias, { exact: true }) });
  }
}
