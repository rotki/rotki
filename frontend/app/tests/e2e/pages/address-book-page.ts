import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { PillFilterBar } from './pill-filter-bar';
import { RotkiApp } from './rotki-app';

type Scope = 'global' | 'private';

async function dismissErrorIfShown(page: Page): Promise<void> {
  const okBtn = page.locator('[data-testid=message-dialog-ok]');
  // Wait briefly for a delayed popup to appear; if none, move on.
  try {
    await okBtn.waitFor({ state: 'visible', timeout: 500 });
  }
  catch {
    return;
  }
  await okBtn.click();
  await okBtn.waitFor({ state: 'detached', timeout: TIMEOUT_SHORT }).catch(() => undefined);
}

async function confirmDialog(page: Page): Promise<void> {
  const dialog = page.locator('[data-testid=bottom-dialog]');
  await dialog.locator('[data-testid=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  await dismissErrorIfShown(page);
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-testid=confirm-dialog]');
  await confirmDialogEl.locator('[data-testid=button-confirm]').click();
  await confirmDialogEl.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

export class AddressBookPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'address-book-manager');
  }

  private table() {
    return this.page.getByTestId('address-book-table');
  }

  private rows() {
    return this.table().locator('tbody tr[data-id="row"]');
  }

  rowFor(addressOrName: string) {
    // For 0x... addresses match by the leading hex, otherwise match the full text.
    const needle = addressOrName.startsWith('0x') ? addressOrName.slice(0, 12) : addressOrName;
    return this.rows().filter({ hasText: needle });
  }

  rowByName(name: string) {
    return this.rows().filter({ hasText: name });
  }

  async selectScope(scope: Scope): Promise<void> {
    await this.page.locator(`[data-testid=address-book-scope-tab][data-key="${scope}"]`).click();
    // Wait for any in-flight fetch to settle by checking row attachment.
    await this.page.waitForTimeout(200);
  }

  async expectScopeActive(scope: Scope): Promise<void> {
    const tab = this.page.locator(`[data-testid=address-book-scope-tab][data-key="${scope}"]`);
    await expect(tab).toHaveAttribute('aria-selected', 'true');
  }

  async openAddDialog(): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.page.getByTestId('address-book-add').click();
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
    await expect(dialog.getByText('The address field cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The name field cannot be empty')).toBeVisible();
  }

  async addEntry(opts: { address: string; name: string }): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.page.getByTestId('address-book-add').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await this.page.getByTestId('address-book-form-address').locator('input').first().fill(opts.address);
    await this.page.getByTestId('address-book-form-name').locator('input').fill(opts.name);
    await confirmDialog(this.page);
  }

  async editEntry(address: string, newName: string): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.rowFor(address).first().locator('[data-testid=row-edit]').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    // Wait for the dialog to bind to the editable row's data; the title flips
    // from the empty "Add" form to "Edit address book entry" once that lands.
    await expect(dialog.locator('h5').filter({ hasText: /edit/i })).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    const nameInput = this.page.getByTestId('address-book-form-name').locator('input');
    await nameInput.fill(newName);
    await confirmDialog(this.page);
  }

  async deleteEntry(address: string): Promise<void> {
    await this.rowFor(address).first().locator('[data-testid=row-delete]').click();
    await confirmDelete(this.page);
    await expect(this.rowFor(address)).toHaveCount(0);
  }

  /**
   * The chain filter, now a pill in the shared bar rather than a selector of its own.
   *
   * `search` is the chain's display name, which is what the checklist matches on, while the value
   * ticked is the chain id the request carries.
   */
  async filterByChain(chainId: string, chainName: string): Promise<void> {
    const filter = new PillFilterBar(this.page);
    await filter.addField('blockchain');
    await filter.selectValue(chainId, chainName);
    await filter.closeEditor('blockchain');
    await filter.expectPillVisible('blockchain');
  }

  async clearChainFilter(): Promise<void> {
    const filter = new PillFilterBar(this.page);
    await filter.removePill('blockchain');
    await filter.expectNoPill('blockchain');
  }

  /** Filters by a substring of the entry name, which is typed rather than picked. */
  async filterByName(name: string): Promise<void> {
    const filter = new PillFilterBar(this.page);
    await filter.addField('nameSubstring');
    await filter.typeTextValue(name);
    await filter.closeEditor('nameSubstring');
    await filter.expectPillVisible('nameSubstring');
  }

  async clearFilters(): Promise<void> {
    await new PillFilterBar(this.page).clearAll();
  }

  /** Waits for the table to settle on a row count, which a filter changes asynchronously. */
  async expectVisibleRowCount(expected: number): Promise<void> {
    await expect.poll(async () => this.visibleRowCount(), { timeout: TIMEOUT_MEDIUM }).toBe(expected);
  }

  async expectRow(address: string, name?: string): Promise<void> {
    const row = this.rowFor(address).first();
    await expect(row).toBeVisible();
    if (name)
      await expect(row).toContainText(name);
  }

  async expectRowByName(name: string): Promise<void> {
    await expect(this.rowByName(name).first()).toBeVisible();
  }

  async expectNoRow(address: string): Promise<void> {
    await expect(this.rowFor(address)).toHaveCount(0);
  }

  async visibleRowCount(): Promise<number> {
    return this.rows().count();
  }

  async goToNextPage(): Promise<void> {
    await this.table().locator('[data-id=table-pagination-next]').first().click();
  }

  async expectNextPageEnabled(enabled: boolean): Promise<void> {
    const next = this.table().locator('[data-id=table-pagination-next]').first();
    if (enabled)
      await expect(next).toBeEnabled();
    else
      await expect(next).toBeDisabled();
  }
}
