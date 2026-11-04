import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmDialog, discardChanges } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

/**
 * Picks a location in a `LocationSelector`.
 *
 * @remarks
 * The option is found by its identifier: names repeat across branches and an option also prints
 * its parent path, so matching on text can land on a different location that mentions the name.
 */
async function selectLocationOption(page: Page, field: Locator, name: string, identifier: string): Promise<void> {
  await field.locator('[data-id=activator]').click();
  const menu = page.locator('[role=listbox]').last();
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
}
