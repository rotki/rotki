import { expect, type Locator, type Page } from '@playwright/test';
import { selectAsset } from '../helpers/utils';
import { ExportSnapshotDialog } from './export-snapshot-dialog';

/**
 * The non-modal snapshot editor page (`/statistics/snapshots/:timestamp`),
 * reached by clicking a snapshot point on the net-worth chart.
 */
export class SnapshotEditorPage {
  constructor(private readonly page: Page) {}

  private get balancesTable() {
    return this.page.locator('[data-testid=snapshot-balances-table]');
  }

  private get locationsDrawer() {
    return this.page.locator('[data-testid=snapshot-locations-drawer]');
  }

  async waitForLoaded(): Promise<void> {
    await this.balancesTable.waitFor({ state: 'visible' });
  }

  /** Picks a location in a LocationSelector (RuiAutoComplete) scoped to `root`. */
  private async selectLocation(root: Locator, location: string): Promise<void> {
    await root.locator('[data-id="activator"]').click();
    await root.locator('input').fill(location);
    const menu = this.page.locator('[role="listbox"], [role="menu"]').last();
    await menu.waitFor({ state: 'visible' });
    const option = menu
      .locator('button[type="button"], [role="option"]')
      .filter({ hasText: new RegExp(location, 'i') })
      .first();
    await option.click();
    await menu.waitFor({ state: 'hidden' });
  }

  /** Deletes a balance row by splitting its value across several locations. */
  async deleteBalanceRowWithSplit(asset: string, allocations: { location: string; amount: string }[]): Promise<void> {
    const row = this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-cy=row-delete]') })
      .first();
    await row.locator('[data-cy=row-delete]').click();
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'visible' });

    await this.page.locator('[data-testid=snapshot-balances-delete-split-toggle] input').check();
    const split = this.page.locator('[data-testid=snapshot-location-split]');
    await split.waitFor({ state: 'visible' });

    const rows = this.page.locator('[data-testid=snapshot-location-split-row]');
    for (const [index, allocation] of allocations.entries()) {
      const splitRow = rows.nth(index);
      await this.selectLocation(splitRow.locator('[data-testid=snapshot-location-split-location]'), allocation.location);
      await splitRow.locator('[data-testid=snapshot-location-split-amount] input').fill(allocation.amount);
    }

    await this.page.locator('[data-cy=button-confirm]').click();
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'hidden' });
  }

  /**
   * Adds a new balance row. The asset's historic USD price must be seeded
   * (see `seedHistoricPrices`) so the value field auto-fills and the form's
   * price fetch resolves — otherwise the value input stays `:disabled="fetching"`.
   */
  async addBalance(asset: string, amount: string, assetId?: string): Promise<void> {
    await this.balancesTable.locator('[data-testid=snapshot-balances-add]').click();
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await selectAsset(this.page, '[data-cy=asset]', asset, assetId);
    await dialog.locator('[data-cy=amount] input').fill(amount);
    // The USD value is derived from the seeded historic price once the fetch
    // settles; wait for it before confirming so validation passes.
    await expect(dialog.locator('[data-cy=secondary] input')).not.toHaveValue('');
    await this.page.locator('[data-cy=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  async editBalanceRow(asset: string, newAmount: string): Promise<void> {
    // Scope to a data row (one with a row-edit action): the "USD Value" column
    // header also contains some asset symbols, so a bare hasText can match it.
    const row = this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-cy=row-edit]') })
      .first();
    await row.locator('[data-cy=row-edit]').click();
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await dialog.locator('[data-cy=amount] input').fill(newAmount);
    await this.page.locator('[data-cy=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  async editLocationRow(location: string, newUsd: string): Promise<void> {
    await this.page.locator('[data-testid=snapshot-summary-edit-locations]').click();
    await this.locationsDrawer.waitFor({ state: 'visible' });
    const row = this.locationsDrawer.locator('tr', { hasText: location }).first();
    await row.locator('[data-cy=row-edit]').click();
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await dialog.locator('[data-testid=edit-location-value] input').fill(newUsd);
    await this.page.locator('[data-cy=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
    await this.page.locator('[data-testid=snapshot-locations-close]').click();
    await this.locationsDrawer.waitFor({ state: 'hidden' });
  }

  get dirtyBadge() {
    return this.page.locator('[data-testid=snapshot-dirty-badge]');
  }

  get mismatchBanner() {
    return this.page.locator('[data-testid=snapshot-summary-reconcile]');
  }

  /** The edit button of a balance data row, used to assert the locked state. */
  balanceEditButton(asset: string) {
    return this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-cy=row-edit]') })
      .first()
      .locator('[data-cy=row-edit]');
  }

  /** Reconcile a sum-mismatch into the pre-selected (largest) location. */
  async reconcile(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-summary-reconcile-apply]').click();
    await this.mismatchBanner.waitFor({ state: 'hidden' });
  }

  async deleteBalanceRow(asset: string): Promise<void> {
    const row = this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-cy=row-delete]') })
      .first();
    await row.locator('[data-cy=row-delete]').click();
    // SnapshotBalanceDeleteDialog (a ConfirmDialog). With a single eligible
    // location it's auto-selected, so confirm is enabled immediately.
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=button-confirm]').click();
    await this.page.locator('[data-cy=confirm-dialog]').waitFor({ state: 'hidden' });
  }

  async discard(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-discard]').click();
    await this.dirtyBadge.waitFor({ state: 'hidden' });
  }

  async save(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-save]').click();
    await this.page.locator('[data-testid=snapshot-save-success]').waitFor({ state: 'visible' });
  }

  async openExport(): Promise<ExportSnapshotDialog> {
    await this.page.locator('[data-testid=snapshot-overflow]').click();
    await this.page.locator('[data-testid=snapshot-export]').click();
    const dialog = new ExportSnapshotDialog(this.page);
    await dialog.waitForVisible();
    return dialog;
  }
}
