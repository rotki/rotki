import type { FixtureManualBalance } from './types';
import { expect, type Page } from '@playwright/test';
import { BigNumber, toSentenceCase } from '@rotki/common';
import { TIMEOUT_LONG } from '../helpers/constants';
import { confirmDialog, formatAmount, selectAsset, updateLocationBalance } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class ManualBalancesPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'balances', 'balances-manual');
  }

  async addBalance(balance: FixtureManualBalance): Promise<void> {
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
    await selectAsset(this.page, '[data-cy=manual-balances-form-asset]', balance.keyword, balance.asset);
    await this.page.locator('[data-cy=manual-balances-form-label] input').fill(balance.label);
    await this.page.locator('[data-cy=manual-balances-form-amount] input').fill(balance.amount);

    for (const tag of balance.tags) {
      const tagsField = this.page.locator('[data-cy=manual-balances-form-tags]');
      const tagsInput = tagsField.locator('input');
      // Click activator to enable the input
      await tagsField.locator('[data-id=activator]').click();
      await tagsInput.fill(tag);
      await tagsInput.press('Enter');
    }

    // Handle location field as autocomplete
    const locationField = this.page.locator('[data-cy=manual-balances-form-location]');
    const locationInput = locationField.locator('input');
    await locationField.locator('[data-id=activator]').click();
    // Use last() since there may be multiple menus, and location menu opens last
    const locationMenu = this.page.locator('[role=menu]').last();
    await locationMenu.waitFor({ state: 'visible' });
    await locationInput.fill(balance.location);
    const locationOption = locationMenu.getByText(balance.location, { exact: false }).first();
    await locationOption.waitFor({ state: 'visible' });
    await locationOption.click();
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
    await expect(this.page.locator('[data-cy=price-refresh]')).not.toBeDisabled();
  }

  async visibleEntries(visible: number): Promise<void> {
    // The total row is added to the visible entries
    await expect(this.page.locator('[data-cy=manual-balances] tbody tr')).toHaveCount(visible + 1);
  }

  async balanceShouldMatch(balances: FixtureManualBalance[]): Promise<void> {
    for (const [i, balance] of balances.entries()) {
      const row = this.page.locator('[data-cy=manual-balances] tbody tr').nth(i);
      await expect(row.locator('[data-cy=manual-balances__amount]')).toContainText(formatAmount(balance.amount));
    }
  }

  async balanceShouldNotMatch(balances: FixtureManualBalance[]): Promise<void> {
    for (const [i, balance] of balances.entries()) {
      const row = this.page.locator('[data-cy=manual-balances] tbody tr').nth(i);
      await expect(row.locator('[data-cy=manual-balances__amount]')).not.toContainText(formatAmount(balance.amount));
    }
  }

  async isVisible(position: number, balance: FixtureManualBalance): Promise<void> {
    const row = this.page.locator('[data-cy=manual-balances] tbody tr').nth(position);

    await expect(row.locator('[data-cy=label]')).toContainText(balance.label);
    await expect(row.locator('[data-cy=manual-balances__amount]')).toContainText(formatAmount(balance.amount));

    await this.page.locator('[data-cy=manual-balances] thead').first().scrollIntoViewIfNeeded();

    await expect(row.locator('[data-cy=manual-balances__location]')).toContainText(toSentenceCase(balance.location));
    await expect(row.locator('[data-cy=list-title]')).toContainText(balance.asset);

    for (const tag of balance.tags) {
      await expect(row.locator('[data-cy=tag]')).toContainText(tag);
    }
  }

  private async getLocationBalances(): Promise<Map<string, BigNumber>> {
    const balances = new Map<string, BigNumber>();
    // Get all data rows (excluding the total row which is typically last)
    const rows = this.page.locator('[data-cy=manual-balances] tbody tr');
    const count = await rows.count();

    // Skip the last row (total row)
    for (let i = 0; i < count - 1; i++) {
      const row = rows.nth(i);
      const locationElement = row.locator('[data-cy=manual-balances__location]');
      const location = await locationElement.getAttribute('data-location');
      if (!location)
        continue;

      const amountText = await row.locator('[data-cy=display-amount]').last().textContent();
      updateLocationBalance(amountText ?? '0', balances, location);
    }

    return balances;
  }

  async getTotals(): Promise<{ total: BigNumber; balances: { location: string; value: BigNumber }[] }> {
    const balancesMap = await this.getLocationBalances();
    let total = new BigNumber(0);
    const balances: { location: string; value: BigNumber }[] = [];

    balancesMap.forEach((value, location) => {
      total = total.plus(value.toFixed(2, BigNumber.ROUND_DOWN));
      balances.push({ location, value });
    });

    return { total, balances };
  }

  async editBalance(position: number, amount: string): Promise<void> {
    const rows = this.page.locator('[data-cy=manual-balances] tbody tr');
    const editButton = rows.nth(position).locator('button[data-cy=row-edit]');

    await editButton.waitFor({ state: 'visible' });
    await expect(editButton).not.toBeDisabled();
    await editButton.click();

    const editForm = this.page.locator('[data-cy=manual-balance-form]');
    await editForm.locator('[data-cy=manual-balances-form-amount] input').clear();
    await editForm.locator('[data-cy=manual-balances-form-amount] input').fill(amount);
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
    await expect(this.page.locator('[data-cy=price-refresh]')).not.toBeDisabled();
  }

  async deleteBalance(position: number): Promise<void> {
    const rows = this.page.locator('[data-cy=manual-balances] tbody tr');
    await rows.nth(position).locator('button[data-cy=row-delete]').click();
    await this.confirmDelete();
  }

  async confirmDelete(): Promise<void> {
    await confirmDialog(this.page, 'Delete manually tracked balance');
  }

  async showsCurrency(currency: string): Promise<void> {
    await this.page.locator('[data-cy=manual-balances]').first().scrollIntoViewIfNeeded();
    await expect(this.page.locator('[data-cy=manual-balances]').first()).toContainText(`${currency} Value`);
    await this.page.locator('[data-cy=manual-balances]').first().waitFor({ state: 'visible' });
  }

  async openAddDialog(): Promise<void> {
    await this.page.locator('[data-cy=manual-balances-add-button]').waitFor({ state: 'visible' });
    await expect(this.page.locator('[data-cy=manual-balances-add-button]')).not.toBeDisabled();
    await this.page.locator('[data-cy=manual-balances-add-button]').click();
  }
}
