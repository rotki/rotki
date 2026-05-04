import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

type Scope = 'global' | 'private';

async function dismissErrorIfShown(page: Page): Promise<void> {
  const okBtn = page.locator('[data-cy=message-dialog__ok]');
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
  const dialog = page.locator('[data-cy=bottom-dialog]');
  await dialog.locator('[data-cy=confirm]').click();
  await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  await dismissErrorIfShown(page);
}

async function confirmDelete(page: Page): Promise<void> {
  const confirmDialogEl = page.locator('[data-cy=confirm-dialog]');
  await confirmDialogEl.locator('[data-cy=button-confirm]').click();
  await confirmDialogEl.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
}

async function pickMenuOption(page: Page, value: string): Promise<void> {
  const menu = page.locator('[role="menu"], [role="listbox"]').last();
  await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
  await menu.locator('button[type="button"]').filter({ hasText: new RegExp(`^${value}$`, 'i') }).first().click();
  await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_SHORT });
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
    await this.page.getByTestId(`address-book-scope-${scope}`).click();
    // Wait for any in-flight fetch to settle by checking row attachment.
    await this.page.waitForTimeout(200);
  }

  async expectScopeActive(scope: Scope): Promise<void> {
    const tab = this.page.getByTestId(`address-book-scope-${scope}`);
    await expect(tab).toHaveAttribute('aria-selected', 'true');
  }

  async openAddDialog(): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.page.getByTestId('address-book-add').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async submitDialog(): Promise<void> {
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
  }

  async cancelDialog(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.locator('[data-cy=cancel]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async expectRequiredErrors(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await expect(dialog.getByText('The address field cannot be empty')).toBeVisible();
    await expect(dialog.getByText('The name field cannot be empty')).toBeVisible();
  }

  async addEntry(opts: { address: string; name: string }): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.page.getByTestId('address-book-add').click();
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await this.page.getByTestId('address-book-form-address').locator('input').first().fill(opts.address);
    await this.page.getByTestId('address-book-form-name').locator('input').fill(opts.name);
    await confirmDialog(this.page);
  }

  async editEntry(address: string, newName: string): Promise<void> {
    await dismissErrorIfShown(this.page);
    await this.rowFor(address).first().locator('[data-cy=row-edit]').click();
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    // Wait for the dialog to bind to the editable row's data; the title flips
    // from the empty "Add" form to "Edit address book entry" once that lands.
    await expect(dialog.locator('h5').filter({ hasText: /edit/i })).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    const nameInput = this.page.getByTestId('address-book-form-name').locator('input');
    await nameInput.fill(newName);
    await confirmDialog(this.page);
  }

  async deleteEntry(address: string): Promise<void> {
    await this.rowFor(address).first().locator('[data-cy=row-delete]').click();
    await confirmDelete(this.page);
    await expect(this.rowFor(address)).toHaveCount(0);
  }

  async filterByChain(chain: string): Promise<void> {
    const filter = this.page.getByTestId('address-book-chain-filter');
    await filter.click();
    await pickMenuOption(this.page, chain);
  }

  async clearChainFilter(): Promise<void> {
    const filter = this.page.getByTestId('address-book-chain-filter');
    // Look for the clear button rendered when an option is selected.
    const clear = filter.locator('button').filter({ hasNot: this.page.locator('text=/.+/') }).first();
    if (await clear.isVisible().catch(() => false)) {
      await clear.click();
    }
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
