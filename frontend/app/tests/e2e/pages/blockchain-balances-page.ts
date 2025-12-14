import type { Page } from '@playwright/test';
import type { BigNumber } from '@rotki/common';
import { waitForNoRunningTasks } from '../helpers/api';
import { parseBigNumber } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class BlockchainBalancesPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'balances', 'balances-blockchain');
    await waitForNoRunningTasks(this.page);
  }

  async getTotals(): Promise<BigNumber> {
    await this.visit();
    const text = await this.page
      .locator('[data-cy=blockchain-asset-balances]')
      .locator('tbody')
      .locator('tr:last-child td:nth-child(2)')
      .locator('[data-cy=display-amount]')
      .textContent();
    return parseBigNumber(text ?? '0');
  }
}
