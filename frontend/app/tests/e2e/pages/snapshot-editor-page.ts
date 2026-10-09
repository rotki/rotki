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
      .filter({ has: this.page.locator('[data-testid=row-delete]') })
      .first();
    await row.locator('[data-testid=row-delete]').click();
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'visible' });

    await this.page.locator('[data-testid=snapshot-balances-delete-split-toggle] input').check();
    const split = this.page.locator('[data-testid=snapshot-location-split]');
    await split.waitFor({ state: 'visible' });

    const rows = this.page.locator('[data-testid=snapshot-location-split-row]');
    for (const [index, allocation] of allocations.entries()) {
      const splitRow = rows.nth(index);
      await this.selectLocation(splitRow.locator('[data-testid=snapshot-location-split-location]'), allocation.location);
      await splitRow.locator('[data-testid=snapshot-location-split-amount] input').fill(allocation.amount);
    }

    await this.page.locator('[data-testid=button-confirm]').click();
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'hidden' });
  }

  /** Deletes a balance row split across `locations`, filling each row with what its location holds. */
  async deleteBalanceRowFillingSplit(asset: string, locations: string[]): Promise<void> {
    await this.balanceDeleteButton(asset).click();
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'visible' });

    await this.page.locator('[data-testid=snapshot-balances-delete-split-toggle] input').check();
    const rows = this.page.locator('[data-testid=snapshot-location-split-row]');
    for (const [index, location] of locations.entries()) {
      const splitRow = rows.nth(index);
      await this.selectLocation(splitRow.locator('[data-testid=snapshot-location-split-location]'), location);
      await splitRow.locator('[data-testid=snapshot-location-split-fill]').click();
    }

    await this.page.locator('[data-testid=button-confirm]').click();
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'hidden' });
  }

  /**
   * Adds a new balance row. The asset's historic USD price must be seeded
   * (see `seedHistoricPrices`) so the value field auto-fills and the form's
   * price fetch resolves — otherwise the value input stays `:disabled="fetching"`.
   */
  async addBalance(asset: string, amount: string, assetId?: string): Promise<void> {
    await this.balancesTable.locator('[data-testid=snapshot-balances-add]').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await selectAsset(this.page, '[data-testid=asset]', asset, assetId);
    await dialog.locator('[data-testid=amount] input').fill(amount);
    // Validation needs the USD value, derived from the seeded price once the fetch settles.
    await expect(dialog.locator('[data-testid=secondary] input')).not.toHaveValue('');
    await this.page.locator('[data-testid=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  /**
   * Edits the balance row for an asset, setting a new amount.
   *
   * @remarks
   * The row must also hold an edit control, not just the asset text: an asset name can also
   * appear in other rows (a header, a total), so filtering on text alone can match those first.
   */
  async editBalanceRow(asset: string, newAmount: string): Promise<void> {
    const row = this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-testid=row-edit]') })
      .first();
    await row.locator('[data-testid=row-edit]').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await dialog.locator('[data-testid=amount] input').fill(newAmount);
    await this.page.locator('[data-testid=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  async editLocationRow(location: string, newUsd: string): Promise<void> {
    await this.page.locator('[data-testid=snapshot-summary-edit-locations]').click();
    await this.locationsDrawer.waitFor({ state: 'visible' });
    const row = this.locationsDrawer.locator('tr', { hasText: location }).first();
    await row.locator('[data-testid=row-edit]').click();
    const dialog = this.page.locator('[data-testid=bottom-dialog]');
    await dialog.waitFor({ state: 'visible' });
    await dialog.locator('[data-testid=edit-location-value] input').fill(newUsd);
    await this.page.locator('[data-testid=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
    await this.page.locator('[data-testid=snapshot-locations-close]').click();
    await this.locationsDrawer.waitFor({ state: 'hidden' });
  }

  /** The summary's headline net worth, as rendered. */
  get netWorth() {
    return this.page.locator('[data-testid=snapshot-summary-net-worth]');
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
      .filter({ has: this.page.locator('[data-testid=row-edit]') })
      .first()
      .locator('[data-testid=row-edit]');
  }

  /** The delete button of a balance data row. */
  balanceDeleteButton(asset: string) {
    return this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-testid=row-delete]') })
      .first()
      .locator('[data-testid=row-delete]');
  }

  /** The chip counting rows the default filters hide (spam, ignored). */
  get hiddenRowsChip() {
    return this.page.locator('[data-testid=snapshot-balances-hidden-count]');
  }

  /** Clears the filters that hide spam and ignored rows. */
  async revealHiddenRows(): Promise<void> {
    await this.hiddenRowsChip.click();
    await this.hiddenRowsChip.waitFor({ state: 'hidden' });
  }

  /** The mismatch banner's offer to remove the rows the gap comes down to. */
  get removeGapRowsButton() {
    return this.page.locator('[data-testid=snapshot-summary-remove-gap-rows]');
  }

  /** The mismatch banner's note that no single location can absorb the difference. */
  get noReconcileTarget() {
    return this.page.locator('[data-testid=snapshot-summary-no-reconcile-target]');
  }

  /** The assets the mismatch banner names as the gap. */
  get gapAssets() {
    return this.page.locator('[data-testid=snapshot-summary-gap-assets]');
  }

  /** Shows the spam and ignored rows from the summary's excluded-value line. */
  async showExcludedRows(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-summary-show-excluded]').click();
  }

  /** Reconcile a sum-mismatch into `location`; nothing is preselected, so it must be picked first. */
  async reconcile(location: string): Promise<void> {
    const apply = this.page.locator('[data-testid=snapshot-summary-reconcile-apply]');
    await expect(apply).toBeDisabled();
    await this.selectLocation(this.mismatchBanner, location);
    await apply.click();
    await this.mismatchBanner.waitFor({ state: 'hidden' });
  }

  async deleteBalanceRow(asset: string): Promise<void> {
    const row = this.balancesTable
      .locator('tr', { hasText: asset })
      .filter({ has: this.page.locator('[data-testid=row-delete]') })
      .first();
    await row.locator('[data-testid=row-delete]').click();
    // A single eligible location is auto-selected, so confirm is enabled immediately.
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=button-confirm]').click();
    await this.page.locator('[data-testid=confirm-dialog]').waitFor({ state: 'hidden' });
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
