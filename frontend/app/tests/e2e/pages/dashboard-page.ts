import { expect, type Page } from '@playwright/test';
import { type BigNumber, Zero } from '@rotki/common';
import { parseBigNumber, updateLocationBalance } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class DashboardPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }

  async getOverallBalance(): Promise<BigNumber> {
    const amountText = await this.page
      .locator('[data-cy=overall-balances__net-worth] [data-cy=display-amount]')
      .textContent();
    return parseBigNumber(amountText ?? '0');
  }

  async getBlockchainBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-cy=blockchain-balances]').waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-cy=blockchain-balance__summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amountText = await element.locator('[data-cy=display-amount]').textContent();
      updateLocationBalance(amountText ?? '0', balances, location);
    }

    return balances;
  }

  async getNonFungibleBalances(): Promise<BigNumber> {
    const nftTable = this.page.locator('[data-cy=nft-balance-table]');
    const nftTableExists = (await nftTable.count()) > 0;

    if (!nftTableExists) {
      return Zero;
    }

    const displayAmount = nftTable.locator('tbody tr:last-child td:nth-child(2) [data-cy=display-amount]');
    const displayAmountExists = (await displayAmount.count()) > 0;

    if (!displayAmountExists) {
      return Zero;
    }

    const amountText = await displayAmount.textContent();
    return parseBigNumber(amountText ?? '0');
  }

  async getLocationBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-cy=manual-balances]').first().waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-cy=manual-balance__summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amountText = await element.locator('[data-cy=display-amount]').textContent();
      updateLocationBalance(amountText ?? '0', balances, location);
    }

    return balances;
  }

  async amountDisplayIsBlurred(): Promise<void> {
    const amountDisplay = this.page.locator('[data-cy=amount-display]').first();
    const filter = await amountDisplay.evaluate(el => getComputedStyle(el).filter);
    expect(filter).toMatch(/^blur/);
  }

  async amountDisplayIsNotBlurred(): Promise<void> {
    const amountDisplay = this.page.locator('[data-cy=amount-display]').first();
    const filter = await amountDisplay.evaluate(el => getComputedStyle(el).filter);
    expect(filter).not.toMatch(/^blur/);
  }

  async percentageDisplayIsBlurred(): Promise<void> {
    await expect(this.page.locator('[data-cy=percentage-display]').first()).toHaveClass(/blur/);
  }

  async percentageDisplayIsNotBlurred(): Promise<void> {
    await expect(this.page.locator('[data-cy=percentage-display]').first()).not.toHaveClass(/blur/);
  }
}
