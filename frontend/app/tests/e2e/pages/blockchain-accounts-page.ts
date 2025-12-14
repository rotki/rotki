import type { FixtureBlockchainAccount } from './types';
import { expect, type Page } from '@playwright/test';
import { BigNumber, Blockchain } from '@rotki/common';
import { waitForNoRunningTasks } from '../helpers/api';
import { TIMEOUT_LONG, TIMEOUT_VERY_LONG } from '../helpers/constants';
import { confirmDialog, updateLocationBalance } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class BlockchainAccountsPage {
  constructor(private readonly page: Page) {}

  async visit(category: string = 'evm'): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'accounts', `accounts-${category}`);
    await waitForNoRunningTasks(this.page);
  }

  async openAddDialog(): Promise<void> {
    // Dismiss any notifications if present
    const dismissButton = this.page.locator('[data-cy=notification_dismiss-all]');
    if (await dismissButton.isVisible()) {
      await dismissButton.click();
    }

    await this.page.locator('[data-cy=notification]').waitFor({ state: 'detached' });
    const addButton = this.page.locator('[data-cy=add-blockchain-account]').first();
    await addButton.waitFor({ state: 'visible' });
    await addButton.click();
  }

  async addAccount(balance: FixtureBlockchainAccount): Promise<void> {
    // Use filter to target the Add blockchain account dialog specifically
    const addAccountDialog = this.page.locator('[data-cy=bottom-dialog]').filter({ hasText: 'Add blockchain account' });
    await addAccountDialog.waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=blockchain-balance-form]').waitFor({ state: 'visible' });

    // Handle blockchain field as autocomplete
    const blockchainField = addAccountDialog.locator('[data-cy=account-blockchain-field]');
    const blockchainInput = blockchainField.locator('input');
    await blockchainField.locator('[data-id=activator]').click();
    await this.page.locator('[role=menu]').waitFor({ state: 'visible' });
    await blockchainInput.fill(balance.chainName);
    const chainOption = this.page.locator('[role=menu]').getByText(balance.chainName, { exact: false }).first();
    await chainOption.waitFor({ state: 'visible' });
    await chainOption.click();

    if (balance.blockchain !== Blockchain.ETH) {
      await this.page.locator('[data-cy=input-mode-manual]').click();
    }

    await expect(this.page.locator('[data-cy=account-address-field] input')).not.toBeDisabled();
    await this.page.locator('[data-cy=account-address-field] input').fill(balance.address);
    await this.page.locator('[data-cy=account-label-field] input').fill(balance.label);

    for (const tag of balance.tags) {
      const tagField = this.page.locator('[data-cy=account-tag-field]');
      const tagInput = tagField.locator('input');
      await tagField.locator('[data-id=activator]').click();
      await tagInput.fill(tag);
      await tagInput.press('Enter');
    }

    await addAccountDialog.locator('[data-cy=confirm]').click();
    await addAccountDialog.waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
  }

  async editAccount(position: number, label: string): Promise<void> {
    const rows = this.page.locator('[data-cy=account-table] tbody tr[class^="_tr_"]:not(tr[class*="_group_"])');
    await rows.nth(position).locator('button[data-cy=row-edit]').click();

    const editDialog = this.page.locator('[data-cy=bottom-dialog]').filter({ has: this.page.locator('[data-cy=blockchain-balance-form]') });
    await editDialog.waitFor({ state: 'visible' });

    const accountLabel = editDialog.locator('[data-cy=account-label-field] input');
    await accountLabel.click();
    await accountLabel.clear();
    await accountLabel.fill(label);
    await editDialog.locator('[data-cy=confirm]').click();
    await editDialog.waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
  }

  async confirmDelete(): Promise<void> {
    await confirmDialog(this.page, 'Account delete');
  }

  async deleteAccount(position: number): Promise<void> {
    // Use labeled-address-display for reliable counting of actual account entries
    const accountAddresses = this.page.locator('[data-cy=account-table] [data-cy=labeled-address-display]');
    const initialCount = await accountAddresses.count();

    // Use the row selector to find the delete button
    const rows = this.page.locator('[data-cy=account-table] tbody tr[class^="_tr_"]:not(tr[class*="_group_"])');
    await rows.nth(position).locator('button[data-cy=row-delete]').click();
    await this.confirmDelete();

    const blockchainSection = this.page.locator('[data-cy=account-table]');
    await blockchainSection.waitFor({ state: 'attached', timeout: TIMEOUT_LONG });
    await blockchainSection.locator('tbody td div[role=progressbar]').waitFor({ state: 'detached', timeout: TIMEOUT_VERY_LONG });

    // Wait for the account count to decrease (confirms delete completed)
    await expect(accountAddresses).toHaveCount(initialCount - 1, { timeout: TIMEOUT_LONG / 2 });
  }

  async isEntryVisible(position: number, balance: FixtureBlockchainAccount): Promise<void> {
    const blockchainSection = this.page.locator('[data-cy=account-table]');
    await blockchainSection.waitFor({ state: 'attached', timeout: TIMEOUT_LONG });
    await blockchainSection.locator('tbody td div[role=progressbar]').waitFor({ state: 'detached', timeout: TIMEOUT_VERY_LONG });

    const rows = blockchainSection.locator('tbody tr[class^="_tr_"]:not(tr[class*="_group_"])');
    const row = rows.nth(position);

    const addressLabel = row.locator('[data-cy=labeled-address-display]');
    await addressLabel.scrollIntoViewIfNeeded();
    await addressLabel.hover();

    const tooltip = this.page.locator('div[role=tooltip]');
    await expect(tooltip.locator('div[role=tooltip-content]')).toContainText(balance.label);
    await expect(tooltip.locator('div[role=tooltip-content]')).toContainText(balance.address);

    for (const tag of balance.tags) {
      await expect(row.locator('[data-cy=tag]')).toContainText(tag);
    }

    await addressLabel.scrollIntoViewIfNeeded();
    await this.page.mouse.move(0, 0); // Move mouse away to close tooltip
  }

  private async getBalances(): Promise<Map<string, BigNumber>> {
    const balances = new Map<string, BigNumber>();
    const categories = ['evm', 'bitcoin'];

    for (const category of categories) {
      await this.visit(category);

      const rows = this.page.locator('[data-cy=account-table] tbody tr[class^="_tr_"]:not(tr[class*="_group_"])');
      const count = await rows.count();

      for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const valueText = await row.locator('[data-cy=usd-value] [data-cy=display-amount]').textContent();
        const asset = await row.locator('[data-cy=account-chain]').first().getAttribute('data-chain');

        if (!valueText || !asset) {
          continue;
        }

        updateLocationBalance(valueText, balances, asset.trim().toLowerCase());
      }
    }

    return balances;
  }

  async getTotals(): Promise<{ total: BigNumber; balances: { blockchain: string; value: BigNumber }[] }> {
    const balancesMap = await this.getBalances();
    let total = new BigNumber(0);
    const balances: { blockchain: string; value: BigNumber }[] = [];

    balancesMap.forEach((value, blockchain) => {
      total = total.plus(value.toFixed(2, BigNumber.ROUND_DOWN));
      balances.push({ blockchain, value });
    });

    return { total, balances };
  }
}
