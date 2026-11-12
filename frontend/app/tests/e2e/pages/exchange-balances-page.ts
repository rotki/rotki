import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

/** The exchange balances page: the exchange cards, the account picker and the asset table. */
export class ExchangeBalancesPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'balances', 'balances-exchange');
  }

  async openExchange(location: string): Promise<void> {
    await this.page.locator(`[data-testid=exchange-balance-card][data-exchange=${location}]`).click();
  }

  picker(): Locator {
    return this.page.locator('[data-testid=exchange-account-picker]');
  }

  options(): Locator {
    return this.page.locator('[data-testid=exchange-account-option]');
  }

  option(account: string): Locator {
    return this.page.locator(`[data-testid=exchange-account-option][data-account="${account}"]`);
  }

  async openPicker(): Promise<void> {
    if (await this.picker().getAttribute('aria-expanded') !== 'true')
      await this.picker().click();
    await expect(this.option('all')).toBeVisible();
  }

  async closePicker(): Promise<void> {
    await this.page.keyboard.press('Escape');
    await expect(this.picker()).toHaveAttribute('aria-expanded', 'false');
  }

  async pick(account: string): Promise<void> {
    await this.openPicker();
    await this.option(account).click();
    await expect(this.picker()).toHaveAttribute('aria-expanded', 'false');
  }

  /** The picker button names the picked account, or all accounts. */
  async expectPicked(name: string): Promise<void> {
    await expect(this.picker()).toHaveText(name, { timeout: TIMEOUT_MEDIUM });
  }

  table(): Locator {
    return this.page.locator('[data-testid=exchange-asset-balances]');
  }

  emptyNotice(): Locator {
    return this.page.locator('[data-testid=exchange-balances-empty]');
  }

  refreshFailedNotice(): Locator {
    return this.page.locator('[data-testid=exchange-balances-refresh-failed]');
  }

  async refresh(): Promise<void> {
    await this.page.locator('[data-testid=refresh-exchange-balances]').click();
  }
}
