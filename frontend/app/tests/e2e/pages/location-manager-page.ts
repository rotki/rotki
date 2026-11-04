import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmDialog, discardChanges, selectLocationOption } from '../helpers/utils';
import { PillFilterBar } from './pill-filter-bar';
import { RotkiApp } from './rotki-app';

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

  /** Filters the tree by a name through the pill bar; an empty term removes the filter. */
  async search(term: string): Promise<void> {
    const bar = new PillFilterBar(this.page);
    if (await bar.pill('locationName').isVisible())
      await bar.removePill('locationName');
    if (term === '')
      return;
    await bar.addField('locationName');
    await bar.typeTextValue(term);
    await bar.closeEditor('locationName');
    await bar.expectPillVisible('locationName');
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

  async saveForm(): Promise<void> {
    await this.formDialog().getByTestId('confirm').click();
  }

  /** Cancels a form holding edits, accepting the prompt to discard them. */
  /** The old and new path of a move, shown in the form until a second save confirms it. */
  moveNotice(): Locator {
    return this.formDialog().getByTestId('location-form-move');
  }

  async discardForm(): Promise<void> {
    await discardChanges(this.page, this.formDialog());
  }

  async expectFormClosed(): Promise<void> {
    await expect(this.formDialog()).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  confirmDialog(): Locator {
    return this.page.getByTestId('confirm-dialog');
  }

  async confirm(): Promise<void> {
    await confirmDialog(this.page);
    await this.confirmDialog().waitFor({ state: 'detached' });
  }

  usageNotice(): Locator {
    return this.page.getByTestId('location-usage');
  }

  async closeUsage(): Promise<void> {
    await this.usageNotice().getByTestId('location-usage-close').click();
    await this.usageNotice().waitFor({ state: 'detached' });
  }

  async openUsageLink(label: string): Promise<void> {
    await this.usageNotice().getByTestId('location-usage-link').filter({ hasText: label }).click();
    await this.usageNotice().waitFor({ state: 'detached' });
  }

  async archiveFromUsage(): Promise<void> {
    await this.usageNotice().getByTestId('location-usage-archive').click();
    await this.usageNotice().waitFor({ state: 'detached' });
  }

  /** Adds an alias through the page's add button and its form. */
  async addAlias(alias: string, name: string, identifier: string): Promise<void> {
    await this.page.getByTestId('location-manager-add').click();
    const form = this.page.getByTestId('location-alias-form');
    await form.waitFor({ state: 'visible' });
    await form.getByTestId('location-alias-name').locator('input').fill(alias);
    await selectLocationOption(this.page, form.getByTestId('location-alias-target'), name, identifier);
    await this.page.locator('[data-testid=bottom-dialog]').filter({ has: form }).getByTestId('confirm').click();
    await form.waitFor({ state: 'detached' });
  }

  aliasRow(alias: string): Locator {
    return this.page.getByTestId('location-aliases-table').locator('tbody tr').filter({ has: this.page.getByText(alias, { exact: true }) });
  }

  /** Deletes an alias, confirming in its row. */
  async deleteAlias(alias: string): Promise<void> {
    await this.aliasRow(alias).getByTestId('location-alias-delete').click();
    await this.aliasRow(alias).getByTestId('location-alias-confirm-delete').click();
  }
}
